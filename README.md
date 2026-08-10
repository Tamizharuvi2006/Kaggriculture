# 🏛️ L+ APEX — Autonomous Kaggriculture Discovery Engine

> An in-game adaptive decision engine built around a frozen L+ 4.1 expert baseline, safe counterfactual exploration, marginal-value evaluation, experience memory, and historical replay intelligence.

---

## 1. Project Mission

L+ APEX was created to solve one specific limitation of deterministic Kaggriculture agents:

> **A strong expert baseline can win consistently, but a static policy eventually becomes the ceiling.**

Our objective is **NOT** to replace the L+ 4.1 expert blindly.

The objective is to build an autonomous system that can:

1. Observe the current game state.
2. Understand economic and temporal opportunity cost.
3. Generate alternative actions.
4. Compare alternatives against the L+ expert plan.
5. Reject unsafe actions before execution.
6. Execute only controlled, zero-capital-cost deviations.
7. Observe the real outcome.
8. Store the experience.
9. Improve future decision selection without retraining after every match.
10. Eventually use historical Kaggriculture trajectories to improve its value model.

The L+ expert therefore remains the **safety anchor**, while APEX becomes the **discovery layer**.

---

## 2. Immutable Benchmark Champions

These files must remain untouched unless explicitly authorized.

| Candidate | Public Score | Role |
|---|---:|---|
| **Clean Candidate** | `1254.1` | Peak leaderboard benchmark (Locked 🔒) |
| **L+ 4.1** | `1108.6` | Frozen expert/control baseline (Locked 🔒) |
| **L+ APEX** | *Autonomous Engine* | Experimental discovery system |

The purpose of APEX is to beat these baselines through empirical evidence, not by modifying them.

---

## 3. Why We Switched From L+ to APEX

The L+ 4.1 strategy became the strongest reliable baseline.

It achieved:
- **1108.6** public leaderboard score.
- Approximately **69.8% win rate** across the analyzed replay set.
- No catastrophic end-game collapses.
- Strong secondary production through pasture/livestock infrastructure.
- Reliable final-step liquidation behavior.

However, forensic analysis showed that L+ was not fundamentally unbeatable. Several losses were extremely narrow:
- $-\$200$
- $-\$692$
- $-\$2,468$

These losses were primarily associated with final-mile timing, inventory movement, and liquidation efficiency.

This created the core hypothesis:
> *L+ is already strong enough that autonomous improvement should focus on small marginal decisions rather than rewriting the entire strategy.*

---

## 4. Initial End-Game Experiment (The End-Game Trap)

The first hypothesis was that L+ could be improved by forcing an end-game market dump via an "End-Game Guard".

It performed badly:
- $\sim -\$5.1\text{k}$ average degradation.
- 0/4 wins against the L+ control.
- Workers were forced into `PASS` states.
- Active harvest/drop sequences were interrupted.
- Cash conversion became worse rather than better.

### Lesson Learned
Never assume an observed weakness should be fixed by directly suppressing movement. The L+ closed-loop schedule already handled terminal liquidation better than the naive guard.

### Decision
**Discard End-Game Guard.** L+ baseline remained frozen.

---

## 5. APEX Architecture & Evolution

The APEX architecture was introduced to transition from static rules to closed-loop, state-aware decision-making:

```text
WorldState
EconomicModel
TimeModel
Planner
Evaluator
Memory
Expert
Policy
Evolution
```

The core decision model became:
$$\text{Action Value} = \text{Expected Profit} + \text{Future Production Value} - \text{Transit Cost} - \text{Opportunity Cost} + \text{Terminal Value}$$

---

## 6. Meta-Regime Detection & Online Adaptation

APEX classifies live match conditions into regimes:
- `HEADSTART`
- `MELON_RUSH`
- `STRAWBERRY_ENGINE`
- `WOOL_ENGINE`
- `LIQUIDATION`
- `BALANCED_HARVEST`

Instead of permanently assuming one commodity is universally best, APEX evaluates prices, production cycles, inventory, available capital, time remaining, opponent behavior, and opportunity cost.

---

## 7. The Imitation Trap & Exploration Failures

### APEX 2.0 & 2.1: The Imitation Trap
Across known and unseen seeds: 100% safety, 100% reproduction, 0% regression, but **0% meaningful divergence**.
*Lesson:* An agent that always agrees with its teacher cannot discover anything new.

### APEX 2.2 & 2.3: Failed Capital Exploration
Naive exploration injected `BUY_SEED`, `BUY_LAND`, and `HIRE` into market action plans.
*Result:* Cash drained to $\$0$, workers stalled, wealth collapsed from $\approx \$128\text{k}$ to $\approx \$4.7\text{k}$ ($0/8$ wins).
*Lesson:* **Cash is operating capacity.** Market-action injection must never bypass the financial safety model. All capital-consuming autonomous exploration was permanently prohibited.

---

## 8. APEX 2.4 Safety Architecture & Invariants

APEX 2.4 introduced strict execution invariants:
1. **Action Purity:** $\text{executed\_market\_actions} == \text{chosen\_plan.market\_actions}$ (no hidden appended commands).
2. **Operating Reserve:** Mandatory operating floor ($\ge \$300.0$) and worker maintenance allowance protected.
3. **Shadow Simulation:** Candidate plans are simulated against the world state before execution.
4. **Zero-Cost Curriculum:** Exploration is restricted to sell quantities, harvest priorities, routing, and zero-capital-cost decisions.

---

## 9. APEX 2.5: Candidate Diversity & First Real Divergence

The planner was upgraded to generate mid-game alternatives.
- Across 8,628 decision steps: **13,720 candidate actions** generated; $\approx 960$ passed safety/UCB filters.
- Rejection distribution: Confidence (85.6%), Terminal (4.02%), Liquidity (3.37%), Worker (0%).
- **First Real Divergence (Step 100, Seed 590244349):**
  - L+: `[]`
  - APEX: `SELL_WHEAT_1`
  - Outcome: L+ = $\$138,095$ vs APEX = $\$138,099$ ($\Delta = +\$4.00$, 100% Safe).

---

## 10. Evaluator Calibration & Marginal Counterfactual Value (MCV)

### Legacy Evaluator Failure
The legacy evaluator calculated raw liquidation spot cash ($3 \times \$95 = \$285$), overvaluing `SELL_FERTILIZER_3` at $\approx +\$287 - \$291$, while actual realized final wealth delta was repeatedly $\$0.00$.

### Marginal Counterfactual Value (MCV) Solution
Redesigned valuation around true marginal delta over the expert's plan:
$$\text{MCV} = \text{Expected Final Wealth}(\text{candidate}) - \text{Expected Final Wealth}(\text{L+ plan})$$

| Metric | Legacy Absolute Evaluator | Marginal Counterfactual Value (MCV) | Improvement |
| :--- | :---: | :---: | :---: |
| **Mean Predicted Advantage** | $+\$267.74$ | $+\$2.05$ | — |
| **Mean Absolute Error (MAE)** | **$\$267.41$** | **$\$1.77$** | **99.3% Error Reduction ✅** |
| **Prediction Bias** | $-\$267.41$ | $-\$1.72$ | — |

---

## 11. Fresh Online MCV Validation (APEX 2.5-G)

A fresh 12-seed online validation tournament (4 Forensic Anchor + 8 Unseen Replay Seeds) demonstrated strong generalization:

| Metric | Fresh 12-Seed Validation Result |
| :--- | :---: |
| **Matches Evaluated** | 12 / 12 |
| **Controlled Divergences Executed** | 12 / 12 (100%) |
| **Positive Match Outcomes** | **6 / 12 (50.0%)** |
| **Neutral Match Outcomes** | **2 / 12 (16.7%)** |
| **Minor Variances ($-\$1$)** | **4 / 12 (33.3%)** |
| **Match Win Rate vs Opponent** | **12 / 12 (100.0% WIN ✅)** |
| **Net Cumulative Wealth Delta** | **$+\$16.00$ Net vs L+ Expert** |
| **Online Prediction MAE** | **$\$3.01$** |
| **Zero Regression Invariant** | **PASSED ✅** |

---

## 12. Complete APEX Architecture Pipeline

```text
                    GAME OBSERVATION
                           │
                           ▼
                     WorldState
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   EconomicModel       TimeModel        OpponentModel
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                     MetaDetector
                           │
                           ▼
                    StrategyAdapter
                           │
                           ▼
                       Planner
                           │
                           ▼
                      SafetyGate
                           │
                           ▼
                 Marginal Value Evaluator (MCV)
                           │
                           ▼
                         UCB
                           │
                           ▼
                 DivergenceController
                           │
                           ▼
                  Shadow Simulation
                           │
                           ▼
                     Execute Action
                           │
                           ▼
                  Experience Memory
                           │
                           ▼
                  Outcome / Calibration
```

---

## 13. Current Safety Rules & Invariants

* **Rule 1 — L+ Fallback:** If APEX cannot prove that a candidate is safe and sufficiently valuable, execute L+.
* **Rule 2 — No Blind Capital Exploration:** APEX must not inject `BUY_SEED`, `BUY_LAND`, or `HIRE`.
* **Rule 3 — Action Purity:** No hidden market commands may be appended.
* **Rule 4 — Operating Reserve:** Cash required for continued operation ($\ge \$300.0 / \$150.0$) remains protected.
* **Rule 5 — Shadow Simulation:** Candidate execution must be validated in simulation prior to dispatch.
* **Rule 6 — Terminal Protection:** Late-game execution preserves the proven L+ terminal liquidation behavior.
* **Rule 7 — Controlled Divergence:** Max 1 divergence/episode, Steps 100–600, Zero Capital Cost only.
* **Rule 8 — No Premature Hardcoding:** A single positive observation must never become a permanent hardcoded rule.

---

## 14. What Is Proven vs. What Is Unproven

### Proven Capabilities ✅
- [x] Zero-regression baseline preservation
- [x] Autonomous candidate generation & safety gating
- [x] Real in-game divergence with safe return to expert schedule
- [x] Zero-capital exploration curriculum
- [x] 99.3% prediction error reduction via Marginal Counterfactual Value (MCV)
- [x] Fresh online generalization (MAE = $\$3.01$, $+\$16.00$ net delta)
- [x] Experience memory & calibration tracking

### Not Yet Proven ⏳
- [ ] Sustained statistical superiority over L+ across hundreds of matches
- [ ] Sustained improvement over Clean Candidate (1254.1)
- [ ] Generalization across radically different meta-regimes
- [ ] Historical replay-derived calibration superiority
- [ ] Live leaderboard rating improvement

---

## 15. Next Milestone: Historical Replay Intelligence (APEX-HIST-1)

The Kaggriculture ecosystem provides daily historical episode datasets (`kaggriculture-episodes-index`).
* **Source:** Daily datasets spanning `2026-07-30` through `2026-08-09`.
* **Schema Probe (APEX-HIST-0 Complete):**
  * `episodes.csv`: Match metadata, final bank/wealth, TrueSkill ratings.
  * `replays.parquet`: Full 720-step granular state/action/observation trajectories.
* **Strategy (APEX-HIST-1):**
  * Ingest recent competitive dates (`2026-08-06` to `2026-08-09`).
  * Filter matches preserving diverse outcomes (wins, narrow losses, high ratings).
  * Extract state-action-outcome tuples to calibrate MCV value distributions.
  * Do NOT turn APEX into a rigid imitation script; treat historical data as probabilistic empirical evidence.

---

## 16. Agent Handoff Guidelines

For any autonomous agent continuing this project:

```text
DO:
  1. Read this README and docs/APEX_EXPERIMENT_HISTORY.md first.
  2. Preserve frozen baselines (Clean Candidate 1254.1 and L+ 4.1 1108.6).
  3. Conduct controlled A/B experiments changing one variable at a time.
  4. Record predicted vs. realized values (MAE and bias).
  5. Enforce all safety invariants and use L+ as default fallback.
  6. Treat historical replay data as probabilistic calibration evidence.

DO NOT:
  1. Modify submission_candidate_l_plus.py or Clean Candidate.
  2. Blindly inject capital-consuming actions (BUY/LAND/HIRE).
  3. Bypass ActionSafetyGate or ShadowSimulator.
  4. Download hundreds of GBs without targeted filtering.
  5. Convert single observations into hardcoded heuristics.
  6. Claim leaderboard superiority without live verified submissions.
```

---

## 17. Current Development State

```text
APEX 2.5
│
├── WorldState                  ✅
├── EconomicModel               ✅
├── TimeModel                   ✅
├── MetaModel                   ✅
├── OpponentModel               ✅
├── StrategyAdapter             ✅
├── Planner                     ✅
├── SafetyGate                  ✅
├── CounterfactualSimulator     ✅
├── MCV Evaluator               ✅
├── DivergenceController        ✅
├── ExperienceMemory            ✅
├── Shadow Simulation           ✅
├── Online MCV Validation       ✅
│
├── Historical Episode Parser   🔜
├── Historical Calibration DB   🔜
├── Historical MCV Calibration  🔜
└── Leaderboard Qualification   ⏳
```
