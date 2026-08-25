# 🧪 EXP-0119: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0119`  
> **Target Baseline**: `APEX-3.5-PROD` ([`submission.py`](file:///D:/kaggriculture/submission.py), SHA256 `78738c1b...`)  
> **Target Archetype**: `CROP_DRIFT` (Priority Engine Rank #2)  
> **Sole Variable Family**: `Resource_Allocation` (Single-variable isolation)  
> **Evidence Source**: [`reports/crop_drift_counterfactual_evidence.json`](file:///D:/kaggriculture/reports/crop_drift_counterfactual_evidence.json)

---

## 1. Verified Mechanism & Counterfactual Forensic Audit

In `APEX 3.5`, `_build_tasks` (line 3898) assigns `PLANT` **Priority 7** (the lowest rank):
* **Identified Queue Bottleneck**: On expansion days (Days 0, 4, 8, 12), workers spend morning hours executing non-critical weed digging (`DIG` p6) and empty pasture preparation (`BUILD_PASTURE` p5) before planting core strawberry seeds.
* **Latency Impact**: Cleared plantable tiles sit idle as `None` for **8.0 hours**, delaying initial growth ticks.
* **Counterfactual Recovery**: Raising `PLANT` priority ahead of preparatory tasks (`DIG`/`PASTURE`) recovers ~6.5 hours of growth velocity, enabling final-cycle strawberry harvests in 35% of seeds.
* **Life-Support Safety Guarantee**: `WATER` (p0/p2), `HARVEST` (p1), `FEED` (p0/p2), and `CARE` (p3) remain strictly higher in priority, ensuring **zero crop/animal starvation**.

---

## 2. Formal Mechanism Hypothesis

> *"Raising `PLANT` task priority from **Priority 7 $\rightarrow$ Priority 4 or 5** (ahead of secondary weed digging and pasture construction, while strictly subordinate to watering, harvesting, and feeding) during expansion/replant windows reduces planting latency from 8.0 hours to ~1.5 hours, recovering late-cycle strawberry harvest ticks without causing maintenance task starvation, PASS volatility, or downside tail risk."*

---

## 3. Pre-Registered Bounded Parameter Space (for GPU Screening)

| Parameter | Baseline (APEX 3.5) | Bounded Search Space | Rationale |
| :--- | :---: | :---: | :--- |
| `plant_priority` | `7` | `[4, 5, 6]` | Shifts planting ahead of `DIG` (p6) and `PASTURE` (p5). |
| `conditional_replant_window` | `False` (Global p7) | `[True, False]` | `True`: active only on Days 0, 4, 8, 12; `False`: global priority. |
| `seed_stock_guard` | `True` | `[True]` | Strictly requires seeds in inventory before task creation. |

*Total Frozen Combinations*: **6 structured variants** (`CAND-119-01` .. `CAND-119-06`).

---

## 4. Pre-Registered 6-Dimension Promotion Gates

To be promoted to production, `EXP-0119` must clear all 6 gates on the frozen holdout suite (`HOLDOUT_V1_N100`, $N \ge 100$, seat-balanced):

1. **Win Rate**: $\Delta \text{WR} \ge +2.5\%$ vs `APEX 3.5` ($p < 0.05$).
2. **Mean Wealth**: $\Delta \mu_{\text{MCV}} \ge +\$2{,}000$ ($p < 0.05$).
3. **Volatility**: $\sigma_{\text{cand}} / \sigma_{\text{base}} \le 1.10$.
4. **Tail Risk**: $\text{MCV}_{p05}(\text{cand}) \ge \text{MCV}_{p05}(\text{base})$.
5. **PASS Inactivity**: $\Delta \text{PASS} \le +0.2\%$, max consecutive PASS turns $\le 3$.
6. **Step Latency**: Mean $\le 20\text{ms}$, Max $\le 200\text{ms}$.

---

## 5. Single-Shot Protocol Contract
- No post-hoc tuning or expanding the 6-variant grid.
- Screen the 6 pre-registered variants on RTX 4050 $\rightarrow$ submit top candidate to official Gate 1 on pinned `kaggle_environments v1.32.6`.
- If Gate 1 fails $\rightarrow$ candidate halted immediately.
