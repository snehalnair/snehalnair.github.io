---
title: "Review Summarization at Scale"
excerpt: "Multilingual ABSA pipeline cutting LLM token usage by 82% and hallucinations to 1.8%."
---

## Situation
LLM summarizers struggled with thousands of redundant reviews, producing hallucinations or overly positive summaries. Capturing nuanced customer sentiment required a more grounded, scalable approach.

## Task
Build a domain-agnostic pipeline that generates explainable, grounded summaries by extracting structured information and removing redundancy, with explicit faithfulness guarantees.

## Action
### Phase 1: Hierarchical Theme Identification
- Zero-Shot Generation: GPT-4 generates candidate themes from a sample of 500 reviews
- Theme Validation: Human annotators label 200 reviews against generated themes; themes with <70% agreement discarded
- Semantic Deduplication: all-mpnet-base-v2 embeddings (768 dim) with cosine similarity >0.85 threshold to merge overlapping themes
- Theme Coverage Metric: % of reviews where at least one theme applies (validated against human labels)

### Phase 2: Structured Extraction (ABSA)
Aspect-Based Sentiment Analysis extracts (Theme, Aspect, Opinion, Sentiment) tuples:
- Primary Extractor: Fine-tuned DeBERTa-v3-base on 5,000 labeled review sentences
- Secondary Validator: GPT-3.5 validates extractions; inter-model agreement: 87.3%
- Conflict Resolution: When models disagree, sample sent to human review queue

### Phase 3: Opinion Clustering (Key Innovation)
- Embedding Model: all-MiniLM-L6-v2 (selected for speed; benchmarked against mpnet with <2% quality loss)
- Clustering: HDBSCAN with min_cluster_size=5, min_samples=3 (tuned via silhouette score)
- Representative Selection: Cluster medoid + 2 diverse samples per cluster
- Reduction: 5,000 reviews -> ~150 representative opinions

### Multilingual Handling
Viator operates globally; 34% of reviews are non-English:
- Language Detection: fastText lid.176 model
- Translation: NLLB-200 for non-English reviews before processing
- Validation: Native speaker spot-checks for top-5 languages (ES, FR, DE, IT, PT)

## Results

| Metric | Baseline (Direct LLM) | Pipeline Method | Method |
| --- | --- | --- | --- |
| Theme Coverage | ~50% | 94.2% | Human annotation on 500 review sample |
| Sentiment Accuracy | 71% | 89% | Compared to 3-annotator majority vote |
| Positivity Bias | 82% positive | 67% positive | Ground truth distribution: 65% positive |
| Hallucination Rate | 12% | 1.8% | Manual audit of 200 summaries |
| Token Usage (per product) | 45K | 8K | 82% reduction via clustering |

## System Design & Architecture
Hybrid ABSA + clustering + LLM summarization pipeline:
- Input: Raw reviews from product database
- Stage 1: Theme identification and validation
- Stage 2: ABSA extraction with dual-model validation
- Stage 3: Opinion clustering and representative selection
- Stage 4: LLM generates summary from representatives only (grounded)
- Output: Structured summary with sentiment distribution and source traceability

## Sentiment Calibration Methodology
1. Collected ground truth sentiment distribution from 1,000 manually labeled reviews
2. Baseline LLM summaries implied 82% positive sentiment (overestimate)
3. Pipeline output: 67% positive, within 2% of ground truth (65%)
4. Statistical test: Chi-square p<0.01 for baseline vs. ground truth; p=0.34 for pipeline vs. ground truth

## Risks & Mitigations

| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Hallucination | Summaries contain invented details | Faithfulness check: every claim traced to source review | Weekly audit of 50 random summaries |
| Theme Overlap | Redundant or confusing themes | Dual-level frequency analysis; merge threshold tuning | Theme drift detection monthly |
| Embedding Quality | Poor clustering affects representatives | Benchmark 3 embedding models; select best silhouette | Cluster quality metrics in dashboard |
| Translation Errors | Non-English reviews misprocessed | NLLB + native speaker validation for top languages | BLEU score monitoring for translation quality |
| Cost/Input Size | Thousands of reviews per product | Clustering reduces to ~150 representatives | Token usage alerts per product |
