---
title: "Cost-Aware Automatic Prompt Optimization (APO)"
excerpt: "Hybrid APE-OPRO prompt optimization for multiclass taxonomy with 18% lower API cost."
---

Situation: LLM prompt quality was manual and hard to scale. A 66-category multiclass taxonomy needed high F1 with strict cost controls.

Task: Automate prompt optimization to maximize Weighted F1 while minimizing inference cost and time.

Action:
- Built a hybrid APE-OPRO architecture (APE high-temperature expansion, OPRO refinement).
- Implemented optimizer-scorer loop (GPT-4 optimizer, GPT-3.5 scorer) with stratified sampling.
- Tuned breadth/depth via ablations; early stopping on diminishing returns.
- Added prompt stability measures (version regression tests, top-3 prompt ensemble).

Results:
- Weighted F1 0.84 (SOTA parity).
- 18% lower API cost vs OPRO-only; 5% lower vs manual iteration.
- 2.8 hours optimization time (down from 4.2 hours).
