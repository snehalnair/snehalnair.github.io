---
layout: post
title: "Evaluating AI agents is not the same as evaluating LLMs"
date: 2026-04-06
---

Most teams building AI agents apply their existing LLM evaluation tooling and wonder why it doesn't tell them much. The problem isn't the tools — it's the unit of analysis.

LLM evaluation scores a (input, output) pair. Agent evaluation needs to score a *trajectory*: the full sequence of turns, tool calls, memory accesses, and decisions that constitute a conversation. A per-turn score of 0.9 across five turns tells you almost nothing about whether a six-turn conversation went well. One contradiction in turn four can undo everything before it.

This post is about what changes when you move from evaluating text generation to evaluating agent behaviour — and how to build the infrastructure for it.

---

## The failure modes that per-turn metrics miss

When we moved our customer service agent from offline evaluation into production pilot, component metrics looked healthy. Intent accuracy was good. Retrieval precision was good. NLI entailment scores on individual outputs were good. End-to-end, the agent was visibly failing in ways none of those metrics captured.

The failures fell into three categories:

**Cross-turn contradiction.** The agent answered a cancellation policy question correctly in turn 2. The customer rephrased it in turn 5. The agent gave a different answer. Per-turn, both responses scored well on their own. Across turns, the conversation was broken.

**Resolved-but-not-resolved queries.** The agent technically answered the question — the policy was stated correctly, the tone was appropriate, CSAT would be positive. But the customer didn't have what they needed to act. They came back within 24 hours asking a follow-up that, with better task framing, the agent could have anticipated. CSAT missed this. Repeat contact rate caught it.

**Scope-creep via adversarial prompting.** A carefully constructed message caused the agent to call a booking modification API during what should have been a read-only policy query. No component-level metric was watching for this — it required a separate tool-call permission gate.

None of these are generation failures. They're *behavioural* failures. Evaluating them requires lifting the analysis from individual outputs to the full trajectory.

---

## Behavioural evaluation: the practical toolkit

### Cross-turn consistency

The setup: take a sampled conversation, identify turns where a factual claim was made, generate paraphrase variants of those questions using an LLM, replay them into the agent at the same conversation state, compare responses with NLI entailment.

```python
from transformers import pipeline

nli = pipeline("text-classification",
               model="cross-encoder/nli-deberta-v3-large")

def consistency_check(response_a: str, response_b: str) -> dict:
    """
    Check whether two responses to the same underlying question
    are consistent with each other.
    Returns entailment score in both directions (A->B and B->A).
    """
    ab = nli({"text": response_a, "text_pair": response_b})
    ba = nli({"text": response_b, "text_pair": response_a})
    return {
        "a_entails_b": ab[0]["label"] == "ENTAILMENT",
        "b_entails_a": ba[0]["label"] == "ENTAILMENT",
        "consistent": (ab[0]["label"] != "CONTRADICTION" and
                       ba[0]["label"] != "CONTRADICTION")
    }
```

The key extension from single-turn NLI evaluation: you run entailment in *both directions*. A→B checks that the second response doesn't contradict the first. B→A checks the reverse. A contradiction in either direction is a consistency failure.

### Task completion without human labels

CSAT requires a survey. Human annotation requires annotators. Both are slow and expensive. For a customer service agent, there is a cheaper signal that is also more causally valid: **did the customer come back within 24 hours with the same question?**

Repeat contact rate, segmented by intent category, is calculable from support logs with no annotation. It captures the failure that CSAT misses — a polite, well-written response that didn't actually resolve the issue.

The weakness: it's a lagging signal. You find out a day later. For high-severity issues, you need something faster — which is where confidence calibration comes in.

### Escalation quality

The naive metric for agent performance is escalation rate — lower is better. This is wrong.

A high escalation rate on a complex multi-policy query is the agent working correctly. A high escalation rate because the knowledge graph doesn't cover a common question is a system failure. Conflating them means you'll optimise the wrong thing.

Categorise every escalation at handoff time:

- **Knowledge gap** — the information wasn't in the system. Fix: expand the knowledge graph.
- **Confidence failure** — the information was there but generation confidence was low. Fix: calibration or retrieval improvement.
- **Policy complexity** — genuinely requires human judgement. Expected behaviour.
- **Sentiment trigger** — escalated because the customer was frustrated. Evaluate separately; optimise tone.
- **Explicit request** — customer asked for a human. Not a failure.

Only knowledge gap and confidence failure count against agent performance. The rest tell you different things and need different responses.

---

## Safety gates: defense in depth

The fundamental principle: **don't rely on the LLM to enforce its own safety constraints**. Prompts can be overridden. A hard constraint at the infrastructure layer cannot be manipulated via text input.

### The three gates

**Input gate** runs before the LLM sees anything. Three checks:

1. PII detection and masking — regex plus NER. Phone numbers, emails, card fragments get replaced with typed placeholders before entering the context window. This is a compliance requirement as much as a safety one.

2. Prompt injection classification — a separate fine-tuned classifier (not the intent router). Injection attempts have recognisable surface patterns: role override ("ignore previous instructions"), context hijacking, instruction smuggling via encoding. A classifier trained on a red-team corpus catches the majority of attempts; borderline cases are escalated.

3. Intent safety routing — separate from the main intent router. Asks: is this query appropriate for automated handling at all? Legal threats, media complaints, safety incidents go to human immediately.

**Tool-call gate** runs before any tool is executed. Enforces a permission matrix: given the classified intent, which tool calls are permitted? A policy inquiry should not trigger booking modification APIs. This is a hard constraint, not a prompt instruction.

```python
TOOL_PERMISSIONS = {
    "policy_inquiry": {"get_policy", "get_faq", "get_product_info"},
    "booking_management": {"get_policy", "get_faq", "get_product_info",
                           "get_booking", "modify_booking"},
    "post_trip_issue": {"get_policy", "get_faq", "get_product_info",
                        "get_booking_history", "create_case"},
    "complaint": {"create_case", "escalate"},
}

def validate_tool_call(intent: str, tool_name: str) -> bool:
    permitted = TOOL_PERMISSIONS.get(intent, set())
    if tool_name not in permitted:
        log_anomaly(intent, tool_name)  # always log scope violations
        return False
    return True
```

When multiple intents fire simultaneously (which an adversarial input may deliberately trigger), take the *intersection* of permitted tools, not the union. This closed a specific attack vector we discovered in red-teaming.

**Output gate** runs on the generated response before delivery:

1. NLI hallucination check — every factual claim checked for entailment against retrieved context. Claims not supported by sources get flagged. Critical claims (policy, pricing, booking terms) in non-entailed output trigger escalation.

2. PII egress scan — a second PII check on the output. The LLM may inadvertently reproduce customer data from context into a response that will be logged.

3. Policy commitment check — pattern matching against a registry of commitments the agent is not authorised to make. "Your refund has been approved" from an agent that can only *request* refunds is a policy violation.

---

## Red-teaming: finding what automation misses

Safety gates catch known failure patterns. Red-teaming finds unknown ones. Running red-team exercises quarterly — with a mix of domain experts and people with no product knowledge — consistently surfaces attack vectors that neither automated evaluation nor production monitoring would catch in reasonable time.

A few practical lessons:

**LLM-assisted attack generation scales your coverage.** Use a strong LLM with a red-team system prompt to generate attack variants at scale. Reserve human red-teamers for domain-specific attacks that require product knowledge. The combination outperforms either approach alone.

**Track severity, not just success rate.** An attack that causes the agent to escalate when it shouldn't is a Low severity finding. An attack that causes it to confirm a booking cancellation it has no authority to make is Critical. The severity distribution tells you whether your gates are failing safely (attacks are succeeding but causing escalation) or dangerously (attacks are causing harmful actions).

**Add successful attacks to a regression suite immediately.** Every red-team finding that isn't fixed before the next release needs a test that runs continuously. Without this, fixed vulnerabilities tend to reappear after model updates or prompt changes.

**The most dangerous attacks exploit multi-turn state.** Single-turn injection attempts are relatively easy to detect. The harder attacks establish a false context over several turns — a user asserts something an earlier agent said, and the current agent treats the assertion as verified fact. Defence: add claim verification for user-asserted facts about prior agent commitments, and escalate rather than accept them at face value.

---

## Production monitoring: what to watch

The goal is to catch regressions before customers encounter them at scale. Two monitoring layers:

**Real-time alerts (minutes):** Hallucination rate spike, injection attempt spike, P95 latency breach, escalation rate spike. These require immediate action and should page the on-call.

**Daily dashboards:** Task completion by intent category, escalation quality breakdown, cross-turn consistency on sampled trajectories. These are for trend analysis, not immediate action.

**Confidence calibration monitoring** is the most undervalued signal. A well-calibrated agent with 0.85 confidence on a response is right approximately 85% of the time. After a model update or a distribution shift, the model may become overconfident — confidence scores look the same but accuracy has dropped, so fewer queries escalate while quality degrades. Track calibration weekly using reliability diagrams on the human audit sample.

**Intent distribution monitoring** catches the failure mode where the world changes but your knowledge doesn't. When a weather event cancels a large batch of tours, the volume of cancellation-related queries spikes within hours. If your knowledge coverage for that category is thin, quality will crater. Monitoring distribution shift in near-real-time lets you pre-warm knowledge coverage before the spike hits.

---

## The metric that matters most for agents

For single-turn content evaluation, the most important metric is NLI entailment — it catches the failures that reach customers. For agents, it's **repeat contact rate within 24 hours**.

CSAT measures whether customers liked the interaction. Repeat contact rate measures whether it actually worked. For a customer service agent, these are not the same thing. Optimising for CSAT produces polite, fluent responses. Optimising for repeat contact rate produces responses that resolve issues.

That shift in what you're measuring changes what you build. It moves engineering effort from response quality to task framing, knowledge coverage, and multi-turn coherence — which is where the real leverage is.

---

*Snehal Nair is an AI Evaluation Specialist based in Edinburgh, with research published at KDD 2024 and KDD 2025.*
