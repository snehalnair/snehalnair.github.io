---
layout: page
title: "AI Evaluation Specialist — Content Quality at Viator"
excerpt: "End-to-end LLM evaluation framework for product descriptions: layered metrics (ROUGE, BERTScore, NLI, G-Eval, SelfCheckGPT), model introspection tooling, and CI/CD integration."
permalink: /portfolio/portfolio-10/
---

## Situation

Viator hosts hundreds of thousands of travel experience listings. Product descriptions and marketing copy are critical to conversion — but inconsistent quality, hallucinated details, and brand-voice drift were measurable problems as LLM-generated rewrites scaled up. There was no systematic evaluation framework: quality was checked manually, sporadically, and without reproducibility.

The challenge was building a rigorous, automated evaluation stack that could catch factual errors, measure semantic fidelity, track marketing copy quality, and surface model failure modes — all at pipeline speed.

## Task

Design and own the end-to-end evaluation framework for LLM-rewritten product descriptions and marketing content. This meant selecting and implementing the right metrics for each content dimension, integrating evaluation into the production rewrite pipeline, and building introspection tooling to enable root-cause analysis when quality regressed.

## Action

### 1. Metric architecture by content dimension

Rather than applying a single metric, I designed a layered evaluation stack where each layer catches a different class of failure:

**Layer 1 — Lexical fidelity (ROUGE-L, BLEU)**
Baseline overlap metrics to catch rewrites that drift too far from source material or drop key product features. ROUGE-L (longest common subsequence) is particularly useful for descriptions where preserving key phrases matters more than n-gram precision. Used as a fast pre-filter — if lexical overlap falls below threshold, the rewrite is flagged before more expensive layers run.

**Layer 2 — Semantic fidelity (BERTScore F1, MoverScore)**
Contextual embedding similarity catches paraphrases that preserve meaning but score poorly on lexical metrics. BERTScore uses BERT token-level cosine similarity; MoverScore applies Word Mover's Distance on contextual embeddings — more robust to reordering in itinerary-style copy. Together these cover the gap between surface similarity and actual meaning preservation.

**Layer 3 — Factual grounding (NLI entailment)**
The most critical layer for product descriptions. An NLI model (DeBERTa-v3-large fine-tuned on MNLI) scores whether each rewritten sentence is *entailed by* the source. Any sentence scoring as contradiction or neutral triggers a hallucination flag. Introducing this layer produced the single largest quality improvement in the pipeline — hallucination rate dropped substantially in the first week of gating.

**Layer 4 — Overall quality (G-Eval / LLM-as-judge)**
GPT-4o as evaluator with chain-of-thought prompting across four dimensions: coherence, fluency, relevance, factual consistency. Used as the final quality gate before content goes live. In calibration studies against human raters, G-Eval scores correlated strongly with human judgement — well enough to substantially reduce manual annotation overhead while maintaining coverage.

**Layer 5 — Reference-free hallucination (SelfCheckGPT)**
For cases with no gold-standard source to compare against (e.g. marketing copy). Samples multiple independent completions and measures cross-consistency — inconsistent facts across samples indicate confabulation. Enabled hallucination detection without requiring a reference document.

### 2. Model introspection tooling

Evaluation metrics tell you *that* quality has degraded — introspection tells you *why*. I built a triage dashboard integrating:

- **Gradient saliency maps** (via Captum) to identify which input tokens most influenced problematic outputs
- **Attention visualisation** (BertViz) to detect when the model attends to irrelevant context
- **Concept activation vectors (TCAV-style probing)** to test whether style concepts (luxury tone, urgency, local specificity) were linearly encoded in transformer layers — used to compare fine-tuned vs base model representations

This tooling cut root-cause triage time dramatically — what previously took hours could typically be resolved within a single focused session.

### 3. Pipeline integration

Integrated the full evaluation stack into the content rewrite CI/CD pipeline:
- Layers 1–3 run as fast pre-filters at batch scale via PySpark
- Layer 4 (G-Eval) runs asynchronously as a quality audit on a random sample plus all flagged items
- Evaluation results written to a metrics store; dashboards alert on rolling 7-day metric degradation

## Results

Introducing NLI entailment gating was the single biggest improvement — hallucination rate dropped substantially within the first week of deployment, and remained the most reliable signal for catching factual errors at scale.

BERTScore and ROUGE-L both improved meaningfully once semantic fidelity became an explicit optimisation target alongside lexical overlap, reflecting better preservation of source intent rather than just surface phrasing.

G-Eval scores correlated strongly with human rater judgement in calibration studies, enabling a significant reduction in manual annotation overhead. Human review was redirected toward edge cases and quarterly calibration audits rather than routine quality checks.

The introspection dashboard reduced the time to identify and fix a quality regression from hours to a single focused session — making it practical to investigate failures rather than simply reraise them as prompt issues.

## Evaluation Metric Reference

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

| Risk | Mitigation |
|---|---|
| NLI false positives on legitimate paraphrases | Calibrated entailment threshold on labelled holdout pairs from the actual pipeline |
| G-Eval score variance across API calls | Each item scored multiple times at temperature=0; final score is median |
| Metric gaming (optimising prompts to score well, not be good) | Quarterly human audit with correlation check against automated scores |
| Saliency maps expensive at scale | Approximate integrated gradients in production; full computation on-demand for triage only |
