---
layout: page
title: "AI Evaluation Specialist — Content Quality at Viator"
excerpt: "End-to-end LLM evaluation framework for product descriptions: layered metrics (ROUGE, BERTScore, NLI, G-Eval, SelfCheckGPT), model introspection tooling, and CI/CD integration that cut hallucination rate by 66%."
---

# AI Evaluation Specialist — Content Quality at Viator

## Situation

Viator hosts over 300,000 travel experience listings. Product descriptions and marketing copy are critical to conversion — but inconsistent quality, hallucinated details, and brand-voice drift were measurable problems as LLM-generated rewrites scaled up. There was no systematic evaluation framework: quality was checked manually, sporadically, and without reproducibility.

The challenge was building a rigorous, automated evaluation stack that could catch factual errors, measure semantic fidelity, track marketing copy quality, and surface model failure modes — all at pipeline speed.

## Task

Design and own the end-to-end evaluation framework for LLM-rewritten product descriptions and marketing content. This meant selecting and implementing the right metrics for each content dimension, integrating evaluation into the production rewrite pipeline, and building introspection tooling to enable root-cause analysis when quality regressed.

## Action

### 1. Metric architecture by content dimension

Rather than applying a single metric, I designed a layered evaluation stack where each layer catches a different class of failure:

**Layer 1 — Lexical fidelity (ROUGE-L, BLEU)**
Baseline overlap metrics to catch rewrites that drift too far from source material or drop key product features. ROUGE-L (longest common subsequence) is particularly useful for descriptions where preserving key phrases matters more than n-gram precision. Threshold: ROUGE-L ≥ 0.72 to pass.

**Layer 2 — Semantic fidelity (BERTScore F1, MoverScore)**
Contextual embedding similarity catches paraphrases that preserve meaning but score poorly on lexical metrics. BERTScore uses BERT token-level cosine similarity; MoverScore applies Word Mover's Distance on contextual embeddings — more robust to reordering in itinerary-style copy. Threshold: BERTScore F1 ≥ 0.88.

**Layer 3 — Factual grounding (NLI entailment)**
The most critical layer for product descriptions. An NLI model (DeBERTa-v3-large fine-tuned on MNLI) scores whether each rewritten sentence is *entailed by* the source. Any sentence scoring as contradiction or neutral triggers a hallucination flag. Reduced hallucination rate from **6.2% → 2.1%** after gating on this layer.

**Layer 4 — Overall quality (G-Eval / LLM-as-judge)**
GPT-4o as evaluator with chain-of-thought prompting across four dimensions: coherence, fluency, relevance, factual consistency. Scores 1–5 per dimension. Achieved **0.87 Spearman correlation** with human rater scores in calibration study (n=500). Used as the final quality gate before content goes live.

**Layer 5 — Reference-free hallucination (SelfCheckGPT)**
For cases with no gold-standard source to compare against (e.g. marketing copy). Samples 5 independent completions and measures cross-consistency — inconsistent facts across samples indicate confabulation. Enabled hallucination detection without requiring a reference document.

### 2. Model introspection tooling

Evaluation metrics tell you *that* quality has degraded — introspection tells you *why*. I built a triage dashboard integrating:

- **Gradient saliency maps** (via Captum) to identify which input tokens most influenced problematic outputs
- **Attention visualisation** (BertViz) to detect when the model attends to irrelevant context
- **Concept activation vectors (TCAV-style probing)** to test whether style concepts (luxury tone, urgency, local specificity) were linearly encoded in transformer layers — used to compare fine-tuned vs base model representations

This tooling reduced average root-cause triage time from ~4 hours to ~35 minutes per incident.

### 3. Pipeline integration

Integrated the full evaluation stack into the content rewrite CI/CD pipeline:
- Layers 1–3 run as fast pre-filters (< 200ms per item at batch scale via PySpark)
- Layer 4 (G-Eval) runs asynchronously as a quality audit on 10% random sample + all flagged items
- Evaluation results written to a metrics store; dashboards alert on rolling 7-day metric degradation

## Results

| Metric | Before | After | Change |
|---|---|---|---|
| Hallucination rate (NLI) | 6.2% | 2.1% | −66% |
| BERTScore F1 (avg) | 0.871 | 0.912 | +4.7% |
| ROUGE-L (avg) | 0.801 | 0.847 | +5.7% |
| G-Eval coherence | 3.9/5 | 4.6/5 | +18% |
| Triage time per incident | ~4 hrs | ~35 min | −85% |
| Human annotation cost | baseline | −62% | automated replacement |

## Evaluation Metric Reference

The table below summarises every metric in the stack, its failure mode coverage, and when to use it.

| Metric | Type | What it catches | Reference needed? |
|---|---|---|---|
| ROUGE-L | Lexical | Key phrase omission, over-abstraction | Yes |
| BLEU | Lexical | Precision-side drift in short copy | Yes |
| BERTScore F1 | Semantic | Meaning drift despite surface similarity | Yes |
| MoverScore | Semantic | Reorder-sensitive semantic gaps | Yes |
| NLI entailment | Factual | Hallucination, contradiction, unsupported claims | Yes |
| G-Eval (LLM-judge) | Holistic | Coherence, fluency, relevance, factual consistency | Optional |
| SelfCheckGPT | Factual | Confabulation (reference-free) | No |
| Saliency/Attribution | Introspection | Model attending to wrong input signals | No |
| TCAV probing | Introspection | Style/tone concept encoding in latent space | No |

## Key Design Decisions & Trade-offs

**Why NLI over perplexity for hallucination?**
Perplexity measures how surprised the model is — not whether the output is factually grounded. A confident hallucination has low perplexity. NLI entailment directly tests logical consistency against the source, which is what matters for product descriptions.

**Why G-Eval over BLEURT or METEOR?**
BLEURT and METEOR correlate well with human judgement on translation tasks but generalise poorly to open-ended marketing copy. G-Eval's chain-of-thought scoring on named dimensions (coherence, fluency, relevance) better mirrors how a content editor would assess a rewrite.

**Why SelfCheckGPT for marketing copy?**
Marketing copy has no canonical reference document — you cannot compare to a "correct" version. SelfCheckGPT exploits the model's own output variance as a hallucination signal, enabling reference-free quality control.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| NLI false positives on legitimate paraphrases | Blocks valid rewrites | Tuned entailment threshold to 0.65 (neutral boundary) via calibration on 1,000 labelled pairs |
| G-Eval score variance across API calls | Unstable quality gates | Each item scored 3× with temperature=0; final score is median |
| Metric gaming (optimising prompts to score well, not be good) | Silent quality decay | Quarterly human audit of 200 random items; correlation ≥ 0.90 required |
| Saliency maps for large models are expensive | Slows triage | Approximate integrated gradients (50 steps) used in production; full 300-step version on-demand only |
