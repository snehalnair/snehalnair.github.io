---
layout: post
title: "Building a production NLP evaluation stack: lessons from rewriting travel listings at scale"
date: 2026-04-06
---

When you ask an LLM to rewrite hundreds of thousands of product descriptions, the bottleneck isn't generation speed or prompt quality — it's knowing whether the output is any good.

ROUGE and BLEU give you a number. That number will mislead you. This post is about building an evaluation stack that doesn't.

---

## The problem with single-metric evaluation

Think of evaluation metrics like medical tests. A single test has a sensitivity/specificity trade-off: optimise for one and you compromise the other. A hallucination-detecting test that flags everything is useless. One that flags nothing is worse.

The mistake most teams make is picking one metric — usually ROUGE because it's familiar — and treating it as a proxy for quality. It isn't. ROUGE measures lexical overlap. A rewrite that preserves every keyword while introducing a factual error will score perfectly on ROUGE and cause a customer complaint.

You need a *stack*: each layer catching a different class of failure, fast layers running first as filters, expensive layers running on survivors and samples.

---

## Layer 1: Lexical metrics (ROUGE-L, BLEU)

Start here not because they're best, but because they're fast and cheap — O(n) string operations at any scale.

**ROUGE-L** (longest common subsequence recall) is the right variant for product descriptions. You care that key phrases from the source appear in the output — recall-orientation matches that. A tour description that drops "wheelchair accessible" or "includes hotel pickup" has failed, regardless of how fluent the prose is.

**BLEU** (modified n-gram precision) is better for short marketing copy where you care about precision — you don't want the model inventing phrases not grounded in the source.

Set these as *floor thresholds*, not targets. If ROUGE-L drops noticeably week-over-week, something has gone wrong upstream — probably a prompt regression or a model update. These metrics won't tell you what's wrong, but they'll tell you something is.

```python
from rouge_score import rouge_scorer
scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
result = scorer.score(reference, hypothesis)
# result.rougeL.fmeasure — set threshold based on calibration on your data
```

---

## Layer 2: Semantic fidelity (BERTScore, MoverScore)

Lexical metrics have a known failure mode: they penalise legitimate paraphrases. "Pick-up from your hotel" and "hotel pickup included" have near-zero n-gram overlap but identical meaning.

**BERTScore** computes token-level cosine similarity between contextual BERT embeddings of reference and hypothesis. Semantically equivalent tokens align strongly even without surface overlap. It correlates well with human judgement on travel content and is robust to the kind of creative paraphrasing a good rewrite model produces.

**MoverScore** applies Earth Mover's Distance (Wasserstein distance) on contextual embeddings. The analogy: imagine meaning as a pile of sand — MoverScore measures how much work it takes to move the sand from one distribution to the other. This makes it more sensitive to reordering than BERTScore, which matters for itinerary-style descriptions where sequence carries meaning.

Run both in the same pass — marginal cost once embeddings are computed.

---

## Layer 3: Factual grounding via NLI entailment

This is the most important layer for product content.

**Natural Language Inference** frames factual checking as a classification problem: given a *premise* (source description) and a *hypothesis* (rewritten sentence), classify as entailment / neutral / contradiction. A rewritten sentence that introduces an unverified claim — "rated #1 in Rome" when the source says nothing about ratings — will score as neutral or contradiction.

We used `DeBERTa-v3-large` fine-tuned on MNLI, applied sentence-by-sentence on rewrites. The impact was immediate: introducing this layer as a gate produced the single largest quality improvement in the pipeline. Hallucinations that had been getting through lexical and semantic checks reliably — confident-sounding but ungrounded additions — were caught here.

The threshold matters. Too strict and legitimate paraphrases get flagged, adding manual review overhead. Too lenient and you're not catching much. Calibrate on a labelled holdout from your actual pipeline, not a benchmark dataset.

```python
from transformers import pipeline
nli = pipeline("text-classification", model="cross-encoder/nli-deberta-v3-large")
result = nli({"text": premise, "text_pair": hypothesis})
# result[0]['label'] in ['ENTAILMENT', 'NEUTRAL', 'CONTRADICTION']
```

One subtlety: apply NLI at sentence level, not paragraph level. The model's attention degrades over long spans, and you want fine-grained flags for triage — a paragraph-level score hides where the problem is.

---

## Layer 4: Reference-free quality (G-Eval, SelfCheckGPT)

The first three layers all require a reference document. Marketing copy often doesn't have one — there's no "correct" version of a tagline to compare against. You need reference-free metrics.

**G-Eval** uses a strong LLM (GPT-4o) as evaluator with chain-of-thought prompting. You define evaluation dimensions explicitly — coherence, fluency, relevance, factual consistency — and ask the model to score 1–5 with reasoning before the number. The reasoning step matters: it reduces variance and catches cases where a plausible-sounding score is masking an incoherent rationale.

In calibration studies comparing G-Eval to human raters, correlation was strong enough to replace the majority of routine human annotation, while keeping humans on edge cases and periodic audits. The cost saving was meaningful; the quality signal held.

**SelfCheckGPT** takes a completely different approach: sample the model multiple times independently, then measure consistency across samples. Hallucinated facts tend to be inconsistent — the model will say "established in 1987" in one sample and "founded in 1992" in another. Real facts are stable. No reference needed.

This is your best tool for marketing copy where ground truth doesn't exist.

---

## Layer 5: Model introspection (when metrics aren't enough)

Metrics tell you *that* quality has degraded. They don't tell you *why*. For root-cause analysis, you need to look inside the model.

**Gradient saliency** (integrated gradients via Captum) answers: which input tokens most influenced this specific output? When a description hallucinates a feature, saliency maps often reveal the model was attending to irrelevant context — a nearby listing in the prompt, a formatting token, a date.

**Attention visualisation** (BertViz) lets you inspect which layers are doing what. Not all attention is informative — early layers handle syntax, middle layers semantics, late layers task-specific patterns. Knowing which layer is misbehaving narrows the debugging surface considerably.

**TCAV-style concept probing** answers a subtler question: is the model's internal representation encoding the concepts you think it is? Train a linear probe on labelled activations — "luxury tone" positive/negative examples — and test whether that concept is linearly separable in a given layer. If your fine-tuned model shows a stronger luxury-tone signal than the base model at certain layers but not others, that tells you which layers the fine-tuning actually changed.

These tools are not for production-scale batch evaluation. Use them in triage mode: when a metric regresses, pull a sample of flagged items, run introspection on those, identify the pattern, fix the root cause. The payoff is that what previously took a full day of investigation can typically be resolved in a single session.

---

## What the full stack looks like

```
Source description
      │
      ▼
 [ROUGE-L + BLEU]  ←── fast lexical filter
      │ pass
      ▼
 [BERTScore F1]    ←── semantic similarity
      │ pass
      ▼
 [NLI entailment]  ←── factual grounding
      │ pass / flag
      ▼
 [G-Eval sample]   ←── random sample + all flagged, async
      │
      ▼
 [SelfCheckGPT]    ←── marketing copy only, no reference
      │
      ▼
 [Saliency/Attn]   ←── on-demand for triage only
```

The first three layers are fast enough to run synchronously at batch scale with PySpark. G-Eval runs asynchronously on a sample. Introspection tools run on demand, not inline.

---

## The metric that matters most

After running this stack in production, the clearest lesson is: **NLI entailment is the most important metric for factual content**. Not BERTScore, not G-Eval, not ROUGE.

ROUGE and BLEU are necessary but insufficient — they catch structural problems, not semantic ones. BERTScore is excellent for measuring how much meaning is preserved. But neither will catch a confident hallucination. Only entailment-based checking directly tests the logical relationship between source and output.

If you're evaluating LLM-generated content against a reference and you're only using n-gram metrics, you're flying blind on the failures that will actually reach your users.

---

*Snehal Nair is an AI Evaluation Specialist based in Edinburgh, with research published at KDD 2024 and KDD 2025.*
