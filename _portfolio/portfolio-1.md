---
title: "Cost-Aware Automatic Prompt Optimization (APO)"
excerpt: "Hybrid APE-OPRO prompt optimization for multiclass product taxonomy with 18% lower API cost."
---

Situation: Multiclass product taxonomy (66 categories) with limited labeled data required scalable prompt optimization and cost control.

Task: Automate optimal prompt generation to maximize Weighted F1 while minimizing inference cost.

Action:
- Built a hybrid APE-OPRO architecture to avoid cold-start iterations.
- Implemented optimizer-scorer loop (GPT-4 optimizer, GPT-3.5 scorer) with stratified sampling.
- Ran ablations on breadth/depth to find the best cost-performance point.

Results:
- Matched state-of-the-art performance (Weighted F1 0.84).
- Reduced API cost by 18% vs OPRO alone.
- Cut optimization time to 2.8 hours.
