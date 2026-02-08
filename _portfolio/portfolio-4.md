---
title: "Automated FAQ Extraction (Knowledge Governance System)"
excerpt: "GraphRAG + agentic validation system cutting hallucinations to 2.1%."
---

## Situation
At Viator, the "industry standard" approach of clustering chat logs and summarizing answers failed in production. A pilot revealed that models would hallucinate questions to fit positive sentiment (e.g., claiming food was included because a chat mentioned pets). Because customers are "chaotic browsers" who often chat about one product while viewing another, 30% of support data was contaminated. This led to staleness, inconsistency, and poor coverage for long-tail products.

## Task
Reframe from a simple prompting problem to a system design problem. Build a "Knowledge Lifecycle" system that keeps FAQs true over time and at scale. Targets: 90% reduction in hallucinations and 30% reduction in informational support tickets.

## Action
### Pillar 1: Self-Adaptive RAG (Five-Stage Pipeline)
1. Query Analysis: Classify incoming query by intent type (policy, product-specific, general)
2. Source Selection: Route to appropriate knowledge base (policies, product data, chat history)
3. Retrieval: Hybrid semantic + lexical search with MMR diversification
4. Source Authority Weighting: Score sources by tier - Gold (official policies, weight=1.0), Silver (structured product data, weight=0.7), Bronze (chat logs, weight=0.3)
5. Self-Critique: Retrieved context evaluated for relevance and sufficiency; re-retrieve if confidence <0.8

### Pillar 2: GraphRAG Knowledge Structure
**Ontology Schema:**
- Entity Types: Product, Supplier, Policy, FAQ, Attribute
- Relationship Types: HAS_POLICY, SUPERSEDES, INHERITS_FROM, APPLIES_TO
- Schema Evolution: New entity/relationship types require PR review; backward-compatible migrations only

**Truth Propagation Example:**  
When "Weather Policy" node updates to allow cancellations for >30C heat, all linked Product nodes' FAQs are flagged for regeneration. Graph traversal ensures no orphaned FAQs.

### Pillar 3: Agentic Validation (Coordination Architecture)
| Agent | Trigger | Action | Output | Monitor |
| --- | --- | --- | --- | --- |
| Detect | Hourly cron + webhook on data change | Detect price/policy/API drift | Change event to queue | Change event received |
| Validate | Change event received | Check FAQ accuracy against current data | Validation score + delta | Validation score + delta |
| Correct | Validation score <0.9 or delta >threshold | Trigger FAQ regeneration | New FAQ candidate | New FAQ candidate |
| Govern | New FAQ candidate | Compare to previous; enforce quality gates | Publish or human review | Quality gate outcomes |

Coordination: Redis Streams for event queue; agents are stateless workers consuming from streams. Idempotency keys prevent duplicate processing. Circuit breaker prevents cascade failures (max 100 regenerations/hour).

## Results
| Metric | Baseline | System | Method |
| --- | --- | --- | --- |
| Hallucination Rate | 23% | 2.1% | Manual audit of 500 FAQs |
| Ticket Deflection | — | 34% | A/B test: FAQ-enabled vs. control |
| Product Coverage (Day 1) | 12% | 81% | Products with >=3 FAQs |
| FAQ Freshness | 45 days avg | < 24 hours | Time from source change to FAQ update |
| LLM Latency (serving) | 2.1s | 0ms | Cache hit rate 99.2% |

## Sibling Transfer Validation
1. Similarity threshold: Products must share >80% attribute overlap
2. Validation: Transferred FAQ passed through Validate agent with source product context
3. Confidence scoring: Transferred FAQs marked with confidence; <0.85 triggers human review
4. Audit: 10% random sample of transfers reviewed weekly; current accuracy: 91%

## System Design & Architecture
**Offline Generation / Online Serving Split**
- Offline: FAQ generation runs async; no latency impact on user experience
- Online: FAQs served from Redis cache; cache miss falls back to Elasticsearch
- Consistency: Write-through cache; FAQ updates atomic with cache invalidation

**Graph Update Consistency**
- Transaction Model: Graph updates wrapped in Neo4j transactions; rollback on partial failure
- Batch Processing: Downstream regenerations queued and processed in batches of 50
- Progress Tracking: Each regeneration job tracked; incomplete jobs resumed on worker restart
- Consistency Check: Daily job verifies all FAQs are consistent with current graph state

## Risks & Mitigations
| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Cascading Regeneration | Policy change triggers thousands of updates | Circuit breaker (100/hr max); priority queue for high-traffic products | Regeneration queue depth alerts |
| False Positive Floods | Minor price changes trigger unnecessary work | Dampening layer: ignore changes <5% or within normal variance | False positive rate tracking |
| Regression on Correction | New FAQ worse than stale original | Critic score comparison; auto-rollback if score drops >10% | Before/after score distribution |
| Entity Resolution | Sibling transfer fails on entity mismatch | Fuzzy matching + manual entity linking for top suppliers | Entity resolution accuracy dashboard |
| Graph Staleness | Reality changes faster than graph updates | Agentic monitoring loop; webhook integration with data sources | Graph freshness SLA monitoring |
