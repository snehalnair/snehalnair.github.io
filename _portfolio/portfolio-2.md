---
layout: page
title: "AI Customer Service Agent for Travel (System Design)"
excerpt: "End-to-end agent architecture with GraphRAG knowledge, multi-tier memory, HITL escalation, and <1.5s P95 latency."
---

## Situation
Viator handles millions of customer queries spanning bookings, cancellation policies, product questions, and post-trip issues across 300K+ experiences in 200+ destinations. Customer service was fragmented: agents toggled between 5+ internal tools, knowledge was siloed, and answers were inconsistent. Automating even simple queries required stitching together product data, policies, booking context, and traveler intelligence — none of which existed as a unified system.

The core challenge was not building a chatbot. It was designing a **system of systems** that could serve grounded, personalized answers at scale while knowing when to escalate to a human.

## Task
Design and architect an AI Customer Service Agent that:
1. Resolves 60%+ of Tier-1 queries without human intervention
2. Maintains <1.5s P95 end-to-end response latency
3. Keeps hallucination rate below 2% through grounded generation
4. Provides graceful HITL escalation with full context handoff
5. Operates within a cost budget of <$0.02 per conversation turn

## Action

### System Architecture

The agent is composed of six coordinated subsystems, each designed as an independent service with clear contracts:

<pre class="mermaid">
graph TB
    subgraph Input Layer
        CQ[Customer Query] --> IR[Intent Router]
        CQ --> SG[Safety Gate]
    end

    subgraph Orchestration
        IR -->|intent + confidence| AO[Agent Orchestrator]
        SG -->|safe / blocked / escalate| AO
        AO -->|tool calls| TC[Tool Controller]
    end

    subgraph Knowledge & Data
        TC --> KE[Knowledge Engine<br/>GraphRAG]
        TC --> PD[Product Data<br/>Service]
        TC --> TI[Traveler Intelligence<br/>Tips & Reviews]
    end

    subgraph Memory
        AO --> SM[Session Memory<br/>Conversation Buffer]
        AO --> UP[User Profile<br/>Booking History]
        AO --> KC[Knowledge Cache<br/>Redis]
    end

    subgraph Response
        AO --> RG[Response Generator<br/>Grounded LLM]
        RG --> SG2[Safety Gate<br/>Output Validation]
        SG2 -->|pass| CR[Customer Response]
        SG2 -->|fail| HE[HITL Escalation]
    end

    subgraph Human-in-the-Loop
        AO -->|confidence < threshold| HE
        HE --> HA[Human Agent<br/>+ Context Package]
    end

    style KE fill:#2d6a4f,color:#fff
    style TI fill:#2d6a4f,color:#fff
    style SG fill:#9b2226,color:#fff
    style SG2 fill:#9b2226,color:#fff
    style HE fill:#e76f51,color:#fff
    style AO fill:#264653,color:#fff
</pre>

**Color key:** Green = existing portfolio systems ([Knowledge Engine](/portfolio/portfolio-4/), [Traveler Intelligence](/portfolio/portfolio-5/)); Red = safety layer ([Governance Framework](/portfolio/portfolio-6/)); Orange = HITL; Blue = orchestration.

---

### Subsystem 1: Intent Router

Classifies incoming queries into actionable intents to determine which tools the orchestrator should invoke.

| Intent Category | Example Query | Tools Invoked | % of Volume |
| --- | --- | --- | --- |
| Booking Management | "Can I change my tour date?" | User Profile, Product Data, Policy KB | 28% |
| Policy Inquiry | "What's the cancellation policy?" | Knowledge Engine (GraphRAG) | 22% |
| Product Information | "Does the tour include lunch?" | Knowledge Engine, Product Data | 19% |
| Post-Trip Issue | "The guide didn't show up" | User Profile, HITL Escalation | 15% |
| General / Browsing | "What's fun to do in Rome?" | Traveler Intelligence, Product Data | 12% |
| Complaint / Escalation | "I want a refund now" | HITL Escalation (immediate) | 4% |

**Implementation:** Fine-tuned DeBERTa-v3-base on 15K labeled support transcripts. Multi-label output (primary + secondary intent) with confidence scores. Queries with confidence <0.7 are routed to a fallback LLM classifier before escalation. Prompt optimization uses the [hybrid APE-OPRO approach](/portfolio/portfolio-1/) for the LLM fallback classifier.

**Latency budget:** 15ms (ONNX-optimized, CPU inference).

---

### Subsystem 2: Knowledge Engine (GraphRAG)

This subsystem is detailed in the [Automated FAQ Extraction portfolio piece](/portfolio/portfolio-4/). In the agent context, it serves as the primary knowledge backbone:

- **Graph Structure:** Product -> HAS_POLICY -> Policy, Product -> HAS_FAQ -> FAQ, Policy -> SUPERSEDES -> Policy
- **Retrieval:** Hybrid semantic + lexical search with source authority weighting (Gold/Silver/Bronze)
- **Agent Integration:** The orchestrator issues structured tool calls (`get_policy(product_id, policy_type)`, `get_faqs(product_id, topic)`) rather than free-text retrieval, reducing hallucination surface area

**Key design decision:** FAQs are pre-generated offline and cached, so the agent serves from cache (0ms LLM latency) for 92% of knowledge queries. Only novel or compound queries require real-time LLM generation.

---

### Subsystem 3: Traveler Intelligence

Detailed in the [Active Learning for Traveler Tips portfolio piece](/portfolio/portfolio-5/). In the agent context:

- **Integration point:** When a customer asks about a product experience (not policy), the orchestrator retrieves relevant traveler tips alongside official product data
- **Grounding signal:** Tips provide real-world context that official descriptions lack (e.g., "the stairs are steep — wear good shoes")
- **Presentation:** Tips are attributed ("Based on recent traveler feedback...") and clearly separated from official information

---

### Subsystem 4: Memory Architecture

Three-tier memory system balancing context richness against latency and cost:

<pre class="mermaid">
graph LR
    subgraph Tier 1: Session Memory
        direction TB
        CB[Conversation Buffer<br/>Last 10 turns]
        WM[Working Memory<br/>Extracted entities & intents]
    end

    subgraph Tier 2: User Profile
        direction TB
        BH[Booking History<br/>Active & past bookings]
        CP[Customer Preferences<br/>Language, communication style]
        IH[Interaction History<br/>Past issues & resolutions]
    end

    subgraph Tier 3: Knowledge Cache
        direction TB
        PC[Product Cache<br/>Attributes, pricing, availability]
        PO[Policy Cache<br/>Pre-resolved policy lookups]
        FC[FAQ Cache<br/>Pre-generated answers]
    end

    CB -.->|summarize on overflow| BH
    WM -->|entity lookup| BH
    WM -->|product context| PC

    style CB fill:#264653,color:#fff
    style WM fill:#264653,color:#fff
    style BH fill:#2a9d8f,color:#fff
    style CP fill:#2a9d8f,color:#fff
    style IH fill:#2a9d8f,color:#fff
    style PC fill:#e9c46a,color:#000
    style PO fill:#e9c46a,color:#000
    style FC fill:#e9c46a,color:#000
</pre>

| Tier | Storage | TTL | Latency | Content |
| --- | --- | --- | --- | --- |
| Session Memory | In-process (LRU) | Session duration | <1ms | Last 10 turns + extracted entities |
| User Profile | DynamoDB | Persistent | 5-10ms | Booking history, preferences, past interactions |
| Knowledge Cache | Redis | 24 hours | 2-5ms | Pre-generated FAQs, product attributes, policies |

**Context Window Management:**
- Sliding window of 10 turns with entity extraction (not raw text) for older turns
- Summarization trigger: when token count exceeds 3,000 tokens, older turns are compressed to entity-relationship pairs
- User profile injection: only relevant fields loaded (e.g., for a booking query, load active bookings; for a general query, load preferences only)
- Total context budget: 4,000 tokens max to keep generation fast and focused

---

### Subsystem 5: Agent Orchestrator & Tool Use

The orchestrator is the central coordinator. It receives classified intent + safety clearance, then executes a tool-use loop:

**Query Lifecycle (Swimlane):**

<pre class="mermaid">
sequenceDiagram
    participant C as Customer
    participant SG as Safety Gate
    participant IR as Intent Router
    participant AO as Agent Orchestrator
    participant M as Memory (3-tier)
    participant KE as Knowledge Engine
    participant PD as Product Data
    participant TI as Traveler Intel
    participant LLM as Response LLM
    participant SG2 as Output Safety
    participant H as Human Agent

    C->>SG: Query: "Can I cancel my Rome Colosseum tour if it rains?"
    Note over SG: PII scan + input validation (5ms)
    SG->>IR: Safe query passed
    Note over IR: Intent: policy_inquiry, Confidence: 0.94 (15ms)
    IR->>AO: intent: policy, product: Rome Colosseum, topic: weather cancellation

    par Parallel Tool Calls
        AO->>M: Load session + user profile
        Note over M: Booking #VTR-8821 found (8ms)
        AO->>KE: get_policy(product_id, weather)
        Note over KE: Cache HIT: weather policy (3ms)
        AO->>TI: get_tips(product_id, weather)
        Note over TI: 2 relevant tips found (12ms)
    end

    AO->>LLM: Generate response with context package
    Note over LLM: Grounded generation from policy + tips + booking (800ms)

    LLM->>SG2: Draft response
    Note over SG2: Hallucination check + PII scan (8ms)

    alt Confidence >= 0.85
        SG2->>C: Automated response with policy + traveler tips
    else Confidence < 0.85
        SG2->>H: Escalate with full context package
        H->>C: Human-assisted response
    end
</pre>

**Latency Budget Breakdown:**

| Stage | Target (P95) | Strategy |
| --- | --- | --- |
| Safety Gate (input) | 5ms | Regex + DistilBERT, batched |
| Intent Router | 15ms | ONNX DeBERTa on CPU |
| Memory Lookup | 10ms | DynamoDB + Redis |
| Knowledge Retrieval | 15ms | Redis cache (92% hit rate); Elasticsearch fallback |
| Traveler Tips | 15ms | Pre-indexed in Elasticsearch |
| Response Generation | 1,200ms | GPT-4o-mini with 4K token context cap |
| Safety Gate (output) | 8ms | Same as input gate |
| **Total** | **<1,500ms** | **Parallel tool calls save ~30ms** |

---

### Subsystem 6: HITL Escalation

Not all queries should be automated. The escalation system ensures graceful handoff:

**Escalation Triggers:**

| Trigger | Threshold | Action |
| --- | --- | --- |
| Low intent confidence | <0.7 after fallback classifier | Route to human |
| Low response confidence | <0.85 generation confidence | Route to human |
| Sentiment detection | Anger/frustration score >0.8 | Route to human (priority queue) |
| Explicit request | "Talk to a person" | Immediate route |
| Policy complexity | Multi-policy conflict detected | Route to human |
| Financial impact | Refund >$500 or dispute | Route to human |

**Context Handoff Package:**
When escalating, the agent passes a structured context package to the human agent:
- Conversation transcript (full)
- Detected intent + confidence
- Retrieved knowledge (policies, FAQs, tips)
- Customer profile summary (booking, history)
- Agent's draft response (if generated) with confidence score
- Reason for escalation

This eliminates the "please repeat your issue" problem — human agents start with full context.

---

### Cost Architecture

| Component | Cost Driver | Per-Turn Cost | Optimization |
| --- | --- | --- | --- |
| Intent Router | CPU inference | $0.0001 | ONNX optimization, batch inference |
| Knowledge Retrieval | Cache hit: Redis; Miss: Elasticsearch | $0.0003 | 92% cache hit rate from offline FAQ generation |
| Memory Lookup | DynamoDB reads | $0.0002 | Single-digit ms reads, pay-per-request |
| Response Generation | GPT-4o-mini tokens | $0.012 | 4K token cap; cached responses for repeat queries |
| Safety Gates | CPU inference (2x) | $0.0002 | DistilBERT, batched |
| Infrastructure | ECS Fargate, Redis, DynamoDB | $0.005 | Shared across requests; amortized |
| **Total** | | **$0.018** | **Under $0.02 target** |

**Cost Levers:**
- **Cache hit rate** is the dominant cost driver. At 92% FAQ cache hit, only 8% of knowledge queries require LLM generation
- **Context window size** directly impacts LLM cost. The 4K token cap prevents cost explosion on long conversations
- **Escalation rate** affects total cost: each human-handled turn costs ~$2.50 (agent salary). At 40% deflection, blended cost drops significantly

---

### Tooling & Infrastructure

| Layer | Technology | Rationale |
| --- | --- | --- |
| Orchestration | LangGraph (stateful agent) | Native tool-use, state management, human-in-the-loop primitives |
| Knowledge Graph | Neo4j | Relationship traversal for policy propagation (see [portfolio-4](/portfolio/portfolio-4/)) |
| Vector Store | Elasticsearch (kNN) | Hybrid semantic + lexical; already in stack |
| Cache | Redis Cluster | Sub-5ms reads; write-through from offline pipeline |
| User Data | DynamoDB | Low-latency key-value for user profiles and booking data |
| LLM Gateway | Custom proxy with circuit breaker | Rate limiting, fallback model routing, cost tracking |
| Monitoring | Arize + Grafana | LLM observability, drift detection, safety metrics (see [portfolio-6](/portfolio/portfolio-6/)) |
| Serving | ECS Fargate | Auto-scaling, no GPU required (SLMs on CPU) |

---

## Results (Design Targets & Pilot Metrics)

| Metric | Baseline (No Agent) | Design Target | Pilot Result | Method |
| --- | --- | --- | --- | --- |
| Tier-1 Deflection Rate | 0% | 60% | 43% (pilot) | A/B test on 10K conversations |
| P95 Response Latency | N/A | <1.5s | 1.3s | End-to-end measurement |
| Hallucination Rate | N/A | <2% | 1.9% | Manual audit of 300 responses |
| CSAT (Automated Responses) | N/A | >4.0/5.0 | 4.1/5.0 | Post-conversation survey |
| Cost per Turn | $2.50 (human) | <$0.02 (automated) | $0.018 | Infra + API cost tracking |
| Escalation with Context | 0% (restarts) | 100% | 100% | Context package delivery rate |
| Knowledge Freshness | 45 days avg | <24 hours | <24 hours | Source change to FAQ update |

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- |
| Hallucination in responses | Customer receives incorrect information; brand damage | Grounded generation from cached FAQs; output safety gate; source attribution required | Hallucination rate dashboard; weekly audit of 100 random responses |
| Latency spikes | Poor customer experience; timeout errors | Parallel tool calls; aggressive caching; LLM timeout at 3s with graceful fallback | P95/P99 latency alerts; circuit breaker on LLM gateway |
| Context window overflow | Truncated context leads to poor answers | Sliding window with entity extraction; 4K token hard cap; summarization trigger | Token usage distribution monitoring |
| Cost explosion | LLM API costs exceed budget | Token cap; cache-first architecture; cost alerts at 80% daily budget | Per-turn cost tracking; daily cost dashboard |
| Escalation failures | Customer stuck in loop without human help | Explicit escalation triggers; max 3 automated turns before offering human; sentiment monitoring | Escalation rate by intent; CSAT for escalated conversations |
| Memory staleness | Outdated booking or policy data served | Write-through cache invalidation; real-time booking status via API; policy propagation via GraphRAG | Cache freshness SLA; stale-data incident tracking |
| Adversarial inputs | Jailbreak attempts; prompt injection | Multi-layer safety gate (input + output); encoding detection; multi-turn analysis (see [Governance Framework](/portfolio/portfolio-6/)) | Canary token trigger rate; red team quarterly |

## Cross-Portfolio Integration

This system design integrates and extends several standalone projects into a unified architecture:

| Subsystem | Portfolio Piece | How It Integrates |
| --- | --- | --- |
| Knowledge Engine (GraphRAG) | [Automated FAQ Extraction](/portfolio/portfolio-4/) | Serves as the primary knowledge backbone; pre-generated FAQs cached in Redis; graph traversal for policy resolution |
| Traveler Intelligence | [Active Learning for Traveler Tips](/portfolio/portfolio-5/) | DeBERTa-based tip extraction feeds into agent responses; tips attributed and separated from official info |
| Response Quality | [Review Summarization at Scale](/portfolio/portfolio-3/) | ABSA pipeline informs product understanding; sentiment calibration techniques applied to agent tone |
| Prompt Optimization | [Cost-Aware APO](/portfolio/portfolio-1/) | Hybrid APE-OPRO used for fallback classifier prompt optimization; cost-aware prompt selection |
| Safety & Governance | [Enterprise AI Governance](/portfolio/portfolio-6/) | Safety gate architecture (input + output validation); source authority hierarchies; adversarial defense |
| Engineering Practices | [Cross-Portfolio Practices](/portfolio/portfolio-8/) | A/B testing methodology; model monitoring; embedding selection framework; failure mode analysis |
