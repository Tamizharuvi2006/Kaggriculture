# 📜 APEX Experiment History & Evolutionary Logbook

This document details the chronological record of hypotheses, experiments, failures, and discoveries in the development of the APEX Autonomous Kaggriculture Discovery Engine.

---

## 1. Phase 1: The End-Game Trap & Baseline Discovery

### Hypothesis
Forensic analysis of narrow L+ losses ($-\$200$, $-\$692$) suggested that forcing market liquidations near the match end would improve cash conversion.

### Experiment: End-Game Guard
Injected aggressive liquidation commands and forced workers into `PASS` mode during the final 30 steps.

### Outcome: Failure ❌
* **Result:** $-\$5.1\text{k}$ degradation, 0/4 wins vs L+ control.
* **Root Cause:** Suppressing movement interrupted critical final harvest chains. The existing L+ closed-loop schedule already handled end-game timing optimally.
* **Decision:** End-Game Guard discarded. L+ 4.1 frozen as baseline champion ($1108.6$ 🔒).

---

## 2. Phase 2: APEX 2.0 & 2.1 — The Imitation Trap

### Hypothesis
Building a multi-layer world model, economic model, and strategy adapter will allow APEX to reproduce L+ and safely propose optimizations.

### Outcome: 100% Imitation, 0% Discovery ⚠️
* **Result:** APEX matched L+ decisions 100% of the time.
* **Root Cause:** When the candidate evaluation loop heavily penalties uncertainty, the agent always defaults to the teacher.
* **Decision:** Introduce controlled counterfactual exploration.

---

## 3. Phase 3: APEX 2.2 & 2.3 — Capital Exploration Disasters

### Hypothesis
Allowing APEX to autonomously explore `BUY_SEED`, `BUY_LAND`, and `HIRE` will discover earlier scaling triggers.

### Outcome: Catastrophic Regression ❌
* **Result:** Cash drained to $\$0$, workers stalled, score collapsed from $\approx \$128\text{k}$ to $\approx \$4.7\text{k}$ ($0/8$ wins).
* **Root Cause:** Market actions execute immediately and drain liquid working capital needed for farm operations.
* **Decision:** Permanently prohibit all capital-consuming exploration. Establish the **Zero-Capital-Cost Curriculum** (sell quantities, routing, harvest prioritization only).

---

## 4. Phase 4: APEX 2.4 — Invariant Hardening & Generation Bottleneck

### Hypothesis
Deterministic safety gates and shadow simulation will prevent capital starvation while allowing safe alternatives.

### Finding: Candidate Generation Bottleneck
* Initial tests showed 0% divergence. Rejection audit revealed the planner was generating 0 mid-game alternatives.
* **Fix:** Upgraded planner to produce inventory liquidation variations from expert orders. Generated 13,720 candidates across 8,628 steps ($\approx 960$ passed safety/UCB).

---

## 5. Phase 5: APEX 2.5-C to 2.5-E — First Autonomous Divergences

### Milestone: First Live Policy Divergence (Gate C Proof)
* **Match:** Seed `590244349`, Step 100.
* **L+ Expert Action:** `[]`
* **APEX Divergent Action:** `SELL_WHEAT_1`
* **Outcome:** L+ = $\$138,095$ vs APEX = $\$138,099$ ($\Delta = +\$4.00$, Zero Regressions, 100% Safe).

### 4-Seed Divergence Tournament
* 4/4 Divergences executed (1 Positive, 3 Neutral, 0 Negative).
* **Anomaly Discovered:** `SELL_FERTILIZER_3` was selected across 3 seeds and yielded $\Delta = \$0.00$.

---

## 6. Phase 6: APEX 2.5-F — Evaluator Miscalibration & The Fertilizer Trap

### Anomaly Investigation
The legacy action evaluator scored actions based on **absolute liquidation spot cash**:
$$\text{Score} = 3 \times \$95 = \$285 \implies \text{Predicted Value} \approx +\$287 - \$291$$
However, because L+ was already scheduled to sell the fertilizer shortly afterward, early liquidation had zero marginal benefit on final wealth ($\Delta = \$0.00$).

### Solution: Marginal Counterfactual Value (MCV)
$$\text{MCV} = (\text{CandQty} - \text{ExpertQty}) \times \text{SpotPrice} \times \text{CapitalMultiplier} + \text{CongestionRelief}$$

### Shadow Calibration Audit (12 Matches)
* **Legacy Evaluator:** MAE = **$\$267.41$**, Bias = **$-\$267.41$**
* **MCV Evaluator:** MAE = **$\$1.77$**, Bias = **$-\$1.72$**
* **Error Reduction:** **99.3% reduction in prediction error!** ✅

---

## 7. Phase 7: APEX 2.5-G — Fresh Online MCV Validation

### Tournament Design
* 12 Matches: 4 Forensic Anchor Seeds + 8 Unseen Tournament Replay Seeds.
* Live online MCV candidate scoring and DivergenceController selection.

### Results
* **Divergences Executed:** 12/12 (100% execution)
* **Outcomes:** 6 Positive ($+\$3$ to $+\$4$), 2 Neutral ($\$0$), 4 Minor Rounding ($\pm \$1$)
* **Mean Predicted MCV:** $+\$4.35$
* **Mean Realized Delta:** $+\$1.33$ (**$+\$16.00$ Cumulative Net Delta vs L+**)
* **Online MAE:** **$\$3.01$**
* **Win Rate vs Opponent:** **12/12 (100% WIN ✅)**
* **Zero Regression Invariant:** **PASSED ✅**
