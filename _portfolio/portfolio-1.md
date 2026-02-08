---
title: "Cost-Aware Automatic Prompt Optimization (APO)"
excerpt: "Hybrid APE-OPRO prompt optimization with 18% lower API cost and 0.84 F1."
---

## Situation
LLMs are highly sensitive to prompt phrasing, but prompt engineering is often manual and difficult to scale. At Viator, I transitioned from a multi-label taxonomy to a single-label, multiclass taxonomy to improve product discoverability. Classifying products into 66 exclusive categories with limited labelled data across diverse destinations was challenging, and existing APO frameworks (APE, OPRO, ProTeGi) focused on simple binary tasks without considering the cost-performance trade-offs required in commercial settings.

## Task
Automate optimal prompt generation for product classification, maximizing Weighted F1 while minimizing inference costs. This required evaluating existing APO approaches and engineering a cost-efficient solution suitable for thousands of classifications.

## Action
Built a comprehensive evaluation framework with my team and created a new hybrid architecture:

1. Hybrid APE-OPRO Architecture  
Used APE's semantically diverse prompt generation (temperature=1.0, 20 candidates) to initialize OPRO, avoiding OPRO's costly cold-start iterations. APE provided strong initial prompts, while OPRO refined them through iterative optimization.

2. Optimizer-Scorer Loop with Cost Controls  
- Optimizer Model: GPT-4 for candidate prompt generation (high reasoning capability)
- Scorer Model: GPT-3.5-Turbo for evaluation (10x cost reduction vs. GPT-4)
- Stratified Sampling: Ensured rare categories (e.g., "Submarine Tours") appeared in evaluation batches proportional to commercial importance
- Evaluation Budget: 200 samples per iteration with 3-fold validation to reduce variance

3. Ablation Studies  
Systematically tuned breadth (prompt count: 5, 10, 20) and depth (iterations: 3, 5, 10) to identify diminishing returns. Found optimal configuration at 10 prompts x 5 iterations.

## Results

| Metric | Manual Baseline | OPRO Only | Hybrid APE-OPRO |
| --- | --- | --- | --- |
| Weighted F1 | 0.78 | 0.84 | 0.84 |
| API Cost (per optimization run) | $45 | $52 | $42.60 |
| Optimization Time | N/A | 4.2 hours | 2.8 hours |
| Prompt Stability (across 3 model versions) | N/A | 62% | 78% |

The hybrid method matched state-of-the-art performance while reducing API costs by 18% compared to OPRO alone and 5% compared to manual iteration. Cost reduction calculated as: (OPRO cost - Hybrid cost) / OPRO cost = ($52 - $42.60) / $52 = 18.1%.

## System Design & Architecture
**Architecture Overview:** Modular two-phase system with decoupled optimization and evaluation:
- Phase 1 (Expansion): APE generates 20 diverse candidate prompts using high-temperature sampling
- Phase 2 (Scoring): Miner-Critic loop evaluates candidates, feeding top-3 prompts back into optimizer for refinement
- Termination: Early stopping when F1 improvement < 0.5% for 2 consecutive iterations

**Prompt Stability & Model Version Handling:** Optimized prompts often break when underlying LLMs are updated. Implemented:
- Version Regression Testing: Automated pipeline re-evaluates top prompts against new model versions within 24 hours of release
- Prompt Ensemble: Maintain top-3 prompts; if primary degrades >5% F1, automatically failover to secondary
- Semantic Anchoring: Prompts include explicit format constraints that are less sensitive to model changes

**Evaluation Rigor:** LLM-as-judge has high variance. Mitigated through:
- Multi-Evaluation: Each prompt evaluated 3 times; final score is median to reduce outlier impact
- Confidence Intervals: Report F1 as mean +/- std (e.g., 0.84 +/- 0.02) across evaluation runs
- Human Calibration: Quarterly audit of 100 random classifications against human labels; correlation >0.92

## Risks & Mitigations

| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Cost Explosion | OPRO generates long prompts | APE initialization flattens cost curve; token budget cap at 500 tokens/prompt | Real-time cost dashboard with alerts at 80% budget |
| Label Sensitivity | Performance varies with label format | Standardized templates; ablation on 5 format variants | A/B test new formats before deployment |
