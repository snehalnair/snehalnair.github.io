---
title: "Enterprise AI Governance Framework (Responsible AI)"
excerpt: "Safety gate with 100% coverage and <10ms validation latency."
---

## Situation
As Viator scaled its use of Large Language Models across multiple customer-facing domains, the lack of centralized oversight posed significant brand and safety risks. Disparate teams deployed prompts without standardized safety guardrails, leading to inconsistent outputs and potential exposure to adversarial inputs.

## Task
Design and implement an organization-wide AI Governance and Responsible AI Framework to standardize safety, compliance, and ethical oversight. Goal: 100% of production models pass a rigorous Safety Gate without significantly increasing deployment latency.

## Action
### Pillar 1: Safety Gate Implementation ("Critic-at-the-Edge")
Architecture achieving <10ms validation:
- PII Detection: Regex patterns for common PII (email, phone, SSN) + Presidio for entity recognition (runs in parallel)
- Content Classification: DistilBERT fine-tuned on 10K labeled examples for prohibited content categories
- Bias Detection: Lightweight heuristics (word lists, sentiment skew) for initial screen; heavy model for flagged cases only
- Batching: Requests batched at 10ms intervals; amortizes model inference overhead
- Total Latency: P50: 4ms, P95: 8ms, P99: 12ms (measured over 1M requests)

### Pillar 2: Adversarial Robustness
- Red Team Program: Quarterly adversarial testing by internal security team + external bug bounty
- Encoding Detection: Base64, ROT13, Unicode homoglyph detection in input preprocessing
- Multi-Turn Analysis: Conversation-level context tracking to detect jailbreak attempts across turns
- Canary Tokens: Synthetic "honeypot" prompts in production to detect bypass attempts

### Pillar 3: Source Authority Hierarchies
- Gold Sources: Official policy documents, verified supplier data (weight: 1.0)
- Silver Sources: Structured product metadata, curated FAQs (weight: 0.7)
- Bronze Sources: Chat logs, user reviews (weight: 0.3)
- Conflict Resolution: Higher-tier sources always override lower-tier when contradictions detected

### Pillar 4: Observability & Audit
- Logging: Every inference logged with input hash, output, model version, safety scores
- Monitoring: Arize for real-time safety metric tracking and drift detection
- Audit Trail: Immutable log storage (S3 + Athena) for compliance investigations
- Alerting: PagerDuty integration for safety score anomalies (>2 std from baseline)

## Results

| Metric | Before | After | Method |
| --- | --- | --- | --- |
| Safety Gate Coverage | 34% | 100% | All production endpoints integrated |
| High-Risk Incidents | ~12/month | 1/month | Severity-weighted incident count |
| False Positive Rate | — | 2.3% | Manual review of flagged queries |
| Validation Latency Overhead | — | 8ms P95 | End-to-end measurement |
| Compliance Audit Pass Rate | — | 100% | External audit Q4 2024 |

## System Design & Architecture
Modular Safety Layer integrated into LLMOps pipeline:
- Async Validation: Non-blocking for low-risk queries; blocking for flagged content
- Fallback Responses: Pre-approved safe responses for blocked queries
- A/B Testing: New safety models tested in shadow mode before promotion

## Risks & Mitigations

| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Latency Bloat | Safety checks slow UX | SLMs + batching + parallel execution | P95 latency dashboard |
| False Positives | Harmless queries blocked | HITL review queue; threshold tuning | FP rate by category |
| Adversarial Bypass | Safety layer circumvented | Red team + encoding detection + multi-turn analysis | Canary token trigger rate |
| False Negatives | Harmful content passes | Layered detection; human audit of random sample | Weekly audit of 100 outputs |
| Model Drift | Safety model degrades over time | Continuous retraining on new examples | Safety score distribution tracking |
