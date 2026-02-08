---
title: "Active Learning for Traveler Tips Extraction"
excerpt: "Fine-tuned SLM with 0.84 F1 and 99.3% lower inference cost."
---

## Situation
Traveler tips, valuable, actionable advice, were buried within user reviews. Lack of labeled data made conventional model training impractical.

## Task
Fine-tune a Small Language Model to extract tips with accuracy exceeding few-shot LLM baselines, while minimizing labeling cost and maintaining production-viable inference costs.

## Action
### Model Selection
Evaluated three SLM candidates. Selected DeBERTa-v3-small: best balance of quality and latency for production serving.


| Model | Parameters | Inference Latency | Base F1 (few-shot) |
| --- | --- | --- | --- |
| DistilBERT | 66M | 12ms | 0.68 |
| DeBERTa-v3-small | 44M | 18ms | 0.71 |
| Flan-T5-small | 80M | 25ms | 0.74 |

### Active Learning Workflow
1. Initial Dataset: 4,000 samples with 50% tips (balanced for training stability). 2,000 from LLM-generated labels (GPT-3.5), 2,000 from existing weak labels.
2. Teacher Model: GPT-4 as oracle for disagreement mining
3. Disagreement Mining: Ran inference on 10,000 unlabeled reviews; flagged 1,200 where student prediction diverged from teacher by >0.3 confidence
4. Human Review: Labeled 500 highest-disagreement samples (40 hours annotator time)
5. Iteration: Repeated cycle 3 times until F1 improvement <1% per cycle

### Distribution Calibration
Training on 50/50 balanced data creates probability miscalibration in production (tips are ~8% of reviews). Mitigation:
- Temperature Scaling: Post-hoc calibration on held-out set with true distribution
- Threshold Tuning: Operating threshold set to 0.72 (vs. default 0.5) to optimize precision-recall tradeoff
- Production Sampling: Inference outputs calibrated probabilities, not raw logits

### Teacher Bias Mitigation
LLM-generated labels introduce teacher model biases:
- Bias Detection: Compared LLM labels to human labels on 200 samples; identified systematic under-labeling of negative tips ("avoid...")
- Correction: Augmented training data with human-labeled negative tip examples
- Validation: Final model evaluated only on human-labeled test set (not on LLM labels)

## Results

| Metric | Few-Shot GPT-4 | Fine-Tuned DeBERTa | Method |
| --- | --- | --- | --- |
| F1 Score | 0.76 | 0.84 | Human-labeled test set (n=500) |
| Precision | 0.72 | 0.88 | — |
| Recall | 0.81 | 0.80 | — |
| Inference Cost (per 1K reviews) | $4.20 | $0.03 | API vs. self-hosted |
| Latency (P95) | 1.2s | 22ms | — |

Model achieves 10.5% F1 improvement over few-shot baseline while reducing inference cost by 99.3%.

## System Design & Architecture
- Training: PyTorch + HuggingFace Transformers; 3 epochs, learning rate 2e-5, batch size 32
- Serving: ONNX-optimized model on CPU instances (cost-effective for this workload)
- Pipeline: Batch inference nightly on new reviews; results cached in Elasticsearch

## Risks & Mitigations

| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Class Imbalance | Model biased toward majority class | Balanced training + threshold calibration | Per-class precision/recall weekly |
| Teacher Bias | LLM errors propagated to student | Human validation set; bias detection pipeline | Disagreement rate tracking |
| Diminishing Returns | Continued labeling wastes resources | Stop when F1 improvement <1% per cycle | Learning curve monitoring |
| Distribution Shift | Review language evolves over time | Quarterly re-evaluation on fresh samples | F1 trend monitoring monthly |
