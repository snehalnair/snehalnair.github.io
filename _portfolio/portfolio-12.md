---
layout: page
title: "Media Optimisation — GPT-4V + Multi-Armed Bandit Hero Image Selection"
excerpt: "Combined GPT-4 Vision shortlisting and Bayesian Multi-Armed Bandit to replace static hero image selection with adaptive, CTR-driven optimisation at product scale."
---

## Situation

Viator's product pages each carry a **hero image** — the single image shown in search results and recommendations that most directly influences click-through rate. Most products have galleries of six or more images, but hero selection was historically decided by the **supplier at upload time**: whoever curated the listing picked the first image, and it stayed there.

Two problems compounded each other:

1. **Coverage:** Simply taking the top image from a gallery means stronger candidates sitting further down the gallery are never surfaced for testing.
2. **Scale:** With hundreds of thousands of products across 190+ countries, manual curation was not tractable. Any image-optimisation approach had to run at catalogue scale with minimal human review.

Traditional A/B testing was a poor fit: with multiple candidate images per product, uneven traffic distributions across products, and the need to converge quickly on low-traffic listings, standard frequentist tests were either too slow to reach significance or too rigid to adapt as user preferences shifted seasonally.

## Task

Design a two-stage system that:

1. **Shortlists** the best candidate hero images from each product's gallery automatically — replacing the "take the top image" heuristic with a quality- and relevance-aware filter.
2. **Optimises** across shortlisted candidates adaptively, converging on the highest-CTR image per product without waiting for a fixed-duration A/B test to complete.

Success metric: measurable improvement in click-through rate versus the supplier-curated hero baseline, measured via a controlled holdout.

## Action

### Stage 1 — GPT-4 Vision Shortlisting

The shortlisting stage addressed the coverage problem: systematically evaluating every image in a product's gallery and selecting up to **5 candidates** that complement the current hero image and are worth testing.

GPT-4V was prompted to score each image against a structured rubric:

- **Title relevance** — does the image depict the experience named in the product title?
- **Image quality** — resolution, composition, lighting, absence of watermarks or text overlays
- **Experience representation** — does the image convey the activity and expected atmosphere?
- **Differentiation** — is this image meaningfully different from other shortlisted candidates?

Output was a ranked shortlist of up to 5 candidates per product, formatted for downstream consumption by the MAB layer. The prompt was developed with ablation testing across scoring dimensions, and final calibration was validated against a human-labelled quality benchmark.

### Stage 2 — Bayesian Multi-Armed Bandit Optimisation

The MAB layer addressed the optimisation problem: deciding in real-time which candidate image to show each user, learning from click signals, and converging on a winner without exhausting traffic on clearly underperforming options.

**Algorithm choice — Thompson Sampling (Bayesian):**

Each image arm is modelled as a Beta distribution over click probability:

- Beta(α, β) where α = clicks + 1, β = impressions − clicks + 1
- At each impression, sample from each arm's current Beta posterior; serve the image corresponding to the highest sample
- Posteriors update incrementally with each click/no-click event — no batch retraining required

Thompson Sampling was chosen over UCB and ε-greedy for three reasons:
1. **Naturally adaptive:** probability matching means traffic automatically concentrates on the current best arm as posteriors tighten
2. **No tuning parameter:** UCB requires manual calibration of the exploration coefficient; Thompson Sampling has none
3. **Bayesian credible intervals:** the posterior directly supports the winner-check logic — declare a winner when one arm's 90th-percentile lower bound exceeds all other arms' 90th-percentile upper bounds

**Guardrails:**

Four guardrails were implemented to ensure reliability at product scale:

| Guardrail | Mechanism |
| --- | --- |
| Minimum impressions per arm | No arm declared loser until it has received ≥ 100 impressions, preventing early exits on noise |
| Traffic floor | Each arm guaranteed ≥ 5% of traffic for the duration of the experiment, ensuring even very weak arms accumulate enough signal to exit cleanly |
| Winner confidence threshold | Winning arm must achieve > 90% posterior probability of being best before the experiment closes |
| Holdout baseline | Supplier-curated original hero image always included as one arm, enabling a clean comparison against the pre-optimisation baseline |

**System flow:**

```
Product gallery
    │
    ▼
[GPT-4V shortlisting]
    │
    ├─ Up to 5 candidate images ranked by quality + relevance
    │
    ▼
[MAB experiment initialised]
    │
    ├─ Arms: GPT-4V candidates + supplier-curated hero
    ├─ Each arm initialised: Beta(1, 1) — uninformative prior
    │
    ▼
[Live traffic]
    │
    ├─ Thompson Sampling selects arm per impression
    ├─ CTR events update Beta posteriors in real time
    ├─ Guardrails evaluated continuously
    │
    ▼
[Winner declared at > 90% confidence]
    │
    └─ Winning image promoted to permanent hero
```

**Infrastructure:** Experiment state (per-product arm posteriors) stored in Redis for sub-millisecond read/write at serving time. Assignment and update logic ran as a lightweight sidecar to the product-page serving stack. GPT-4V shortlisting ran as an async batch pipeline triggered at product creation and on significant gallery updates.

## Results

- **Hero image quality at scale:** GPT-4V shortlisting surfaced higher-quality candidates across the catalogue that supplier curation had not prioritised, expanding the effective test set without any manual review burden.
- **Convergence speed vs. A/B testing:** The adaptive allocation of Thompson Sampling reached statistically credible winners significantly faster than a fixed-traffic-split A/B test on the same products, particularly on low-traffic listings where a conventional test would have taken months.
- **Baseline beat rate:** A meaningful proportion of products saw a GPT-4V-shortlisted candidate outperform the original supplier-curated hero on CTR, validating the hypothesis that gallery ordering alone is not a reliable proxy for click performance.

## Design decisions and trade-offs

**Why not a contextual bandit?** A contextual bandit would personalise image selection per user segment (e.g., showing a "guide-led experience" image to users with a history of guided tours). This was considered and deprioritised for V1: adding a context layer multiplies the cold-start problem for each (product × context) pair, and the non-contextual MAB already delivered measurable lift. A contextual extension is the natural V2 — segment by traveler type, market, and device.

**Why GPT-4V rather than a fine-tuned vision model?** Two reasons. First, the shortlisting criteria required multi-dimensional *reasoning* about image content — title-image alignment requires reading the product title and interpreting the image jointly, which is the precise strength of a large vision-language model. A fine-tuned classifier would require labelled training data at catalogue scale, which did not exist. Second, GPT-4V allowed the shortlisting criteria to be iterated cheaply via prompt engineering rather than retraining.

**Reward signal:** CTR is a fast, dense signal (many impressions per day per product) and a direct proxy for the objective (more clicks to product pages). It introduces a bias: a compelling image might drive high CTR but low conversion if it overpromises the experience. A V2 metric design would incorporate downstream signals — bookings per click, review satisfaction — into a composite reward, with CTR as the primary optimisation signal and conversion rate as a guardrail metric.

## Connection to broader portfolio

This project sits at the intersection of three themes that run across the portfolio:

- **Exploration-exploitation under reward sparsity** — the same tension addressed with supervised LTR in [Ranker V2](/portfolio/portfolio-4/) appears here, resolved with a different tool (bandit) appropriate to the smaller action space and faster reward signal.
- **Vision-language models as annotation infrastructure** — the use of GPT-4V as a scalable scoring layer parallels the ABSA and content-quality pipeline work in [portfolio-3](/portfolio/portfolio-3/) and [portfolio-11](/portfolio/portfolio-11/): large multimodal models used to generate structured signal at catalogue scale rather than as end-user-facing features.
- **A/B testing methodology** — the guardrail design (minimum impressions, traffic floors, posterior confidence thresholds) directly applies the experimentation standards documented in [Cross-Portfolio Engineering Practices](/portfolio/portfolio-8/).
