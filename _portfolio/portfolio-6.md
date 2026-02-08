---
title: "Review Summarization at Scale"
excerpt: "Multilingual ABSA pipeline cutting LLM token usage by 82%."
---

Situation: Large-scale review summarization was costly and inconsistent across languages.

Task: Reduce LLM usage while maintaining theme coverage at scale.

Action:
- Built a multilingual ABSA and opinion clustering pipeline.
- Filtered and deduplicated inputs before LLM summarization.
- Added evaluation to preserve coverage and quality.

Results:
- 82% reduction in LLM token usage.
- 94% theme coverage maintained.
