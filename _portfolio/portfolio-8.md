---
title: "Cross-Portfolio Engineering Practices"
excerpt: "Standardized experimentation, monitoring, and reproducibility across ML systems."
---

The following practices are applied consistently across all projects:

## A/B Testing Methodology
- Sample Size: Minimum detectable effect calculated pre-experiment; typical n > 500K sessions
- Duration: Minimum 2 weeks to capture weekly seasonality; 3 weeks for high-stakes changes
- Metrics: Primary metric (e.g., NDCG) + guardrail metrics (latency, error rate, revenue)
- Analysis: Bayesian analysis with 95% credible intervals; sequential testing for early stopping

## Offline-Online Metric Alignment
Offline metrics often don't translate to online gains. Practices:
- Calibration Studies: Quarterly analysis of offline lift vs. online lift across past experiments
- Discount Factor: Apply 0.7x multiplier to offline gains when projecting online impact
- Hybrid Evaluation: Interleaving experiments for ranking models provide online signal without full traffic split

## Model Monitoring & Drift Detection
- Feature Drift: KL divergence between training and serving feature distributions; alert at >0.1
- Prediction Drift: Monitor prediction distribution shift; alert at >5% mean shift
- Performance Monitoring: Delayed labels used to compute online metrics with 7-day lag
- Tooling: Arize for ML observability; custom Grafana dashboards for business metrics

## Data Versioning & Reproducibility
- Dataset Versioning: DVC for training data; each model tagged with data version hash
- Experiment Tracking: MLflow for hyperparameters, metrics, and model artifacts
- Reproducibility: Docker images pinned with exact dependency versions; random seeds logged

## Embedding Model Selection Framework
When selecting embedding models, evaluate:

| Criterion | Benchmark | Threshold |
| --- | --- | --- |
| Task Relevance | Downstream task performance (e.g., retrieval recall) | Top-2 on internal benchmark |
| Latency | P95 inference time | <20ms for online; <100ms for offline |
| Dimension/Cost | Storage and compute cost | Balance with quality needs |
| Language Coverage | Performance on non-English data | >90% of English performance |

## Failure Mode Analysis Template
Each project includes explicit failure mode documentation:
1. Identify top-5 failure modes during design phase
2. Implement detection mechanisms for each failure mode
3. Define automated response (alert, fallback, rollback)
4. Post-mortem template for production incidents
5. Quarterly review of failure mode coverage

## Latency-Accuracy Tradeoff Documentation
All ML systems document their Pareto frontier:
- Model Variants: Test 3+ model sizes/architectures
- Pareto Chart: Plot accuracy vs. latency; identify knee points
- Operating Point: Document chosen tradeoff with business justification
- Fallback Tiers: Define degraded modes for latency spikes
