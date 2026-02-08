---
title: "Real-Time Personalized Search Ranking (Ranker V2)"
excerpt: "Two-stage Learning-to-Rank system with 47ms P95 latency and +9.5% conversion lift."
---

Situation: Legacy search relied on popularity and keyword matching, causing relevance gaps for niche intent.

Task: Build a personalized Learning-to-Rank system with strict latency (<50ms P95) and measurable lift.

Action:
- Built a hybrid retrieval layer (Solr BM25 + Qdrant embeddings) and a two-stage re-ranker.
- Ensembled LightGBM and DCN-v2 to balance sparse and dense features.
- Implemented position bias correction and cold-start fallback tiers.

Results:
- +4.1% NDCG@10 offline; +3.8% online (p<0.01).
- +9.5% conversion lift; P95 latency reduced to 47ms.
