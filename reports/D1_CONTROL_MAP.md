# 🏛️ Variant D.1 Control Authority & Constant Classification Map

This document establishes the exhaustive, line-by-line **Control Authority Map** for `submission.py` / `D1_RESEARCH_COPY.py`.

---

## 🏷️ Classification Taxonomy

* 🟢 **ACTIVE**: Direct, measurable behavioral authority over the agent's live simulation decisions.
* 🟡 **INDIRECT**: Read by downstream planning algorithms or pricing models to evaluate thresholds.
* 🟣 **OVERRIDDEN**: Evaluated by an inner layer, but superseded or clamped by an outer production wrapper.
* 🔴 **INERT**: Evaluated but unreachable, obsolete, or completely suppressed by higher-priority execution rules.

---

## 📋 Comprehensive Constant Matrix

| Parameter / Code Symbol | Classification | Active Location | Empirical Mechanism & Control Authority |
| :--- | :---: | :--- | :--- |
| **`"hands": 13`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Scheduler | Directly dictates total labor force recruitment target (Day 1: 6 workers, Day 5: 10, Day 10: 13). |
| **`"cows": 8`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Scheduler | Sets maximum barn livestock capacity to exactly 8 Dairy Cows ($1,280/day milk cashflow). |
| **`"land_ne_day": 5`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Scheduler | Targets Quadrant #2 (NE) purchase on Day 5 (Step 120). |
| **`"land_sw_day": 10`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Scheduler | Targets Quadrant #3 (SW) purchase on Day 10 (Step 240). |
| **`"strawberry_last_plant": 18`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Plot Engine | Prevents worker planting of new strawberry seeds after Step 432 (Day 18). |
| **`"ongoing_harvest_threshold": 3`**| 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Harvester | Prohibits harvesting strawberry plots until yield accumulation is $\ge 3$ units. |
| **`"opening_wheat": 10`** | 🟢 **ACTIVE** | `DEFAULT_STRATEGY` / Bootstrap | Governs Day 1–2 initial wheat planting wave to fund the first hoe, watering can, and Day 3 cows. |
| **`"fertilizer_roi": 1.5`** | 🟡 **INDIRECT** | `DEFAULT_STRATEGY` / Barn Engine | Compares marginal strawberry yield gain against fertilizer market sell price ($50). |
| **`CROPS` Dict** | 🟡 **INDIRECT** | Core Constants | Provides biological growth steps, seed prices, and maturation intervals to worker pathing. |
| **`ANIMALS` Dict** | 🟡 **INDIRECT** | Core Constants | Provides animal purchase prices ($400 cow, $500 sheep) and production mappings. |
| **`Step 71 Liquidity Rescue`** | 🟢 **ACTIVE** | Top-Level `agent()` Wrapper | Unconditionally liquidates shed milk/fertilizer at Step 71 if cash < $1,000 to guarantee Land #2 on time. |
| **`Step 696 Minimax Liquidation`** | 🟢 **ACTIVE** | Top-Level `agent()` Wrapper | Forces continuous multi-step selling of 100% shed inventory from Step 696 to 719 (0 deadweight loss). |
| **`3-Quadrant Ceiling`** | 🟢 **ACTIVE** | Top-Level `agent()` Wrapper | Intercepts and strips any `BUY_LAND` orders for Quadrant #4 (SE) once 3 quadrants are unlocked. |
| **`SAFE_CASH_BUFFER` Dual-Regime**| 🟢 **ACTIVE** | Top-Level `agent()` Wrapper | Switches market engine between Unconditional Liquidity (cash < buffer) and Momentum Timing (cash >= buffer). |
| **`_APEX35_PRICE_HISTORY`** | 🟢 **ACTIVE** | Top-Level `agent()` Wrapper | Tracks rolling 1-step price derivatives ($v_{\text{straw}}, v_{\text{milk}}$) to detect market crashes. |
| **`"strawberries": 34`** | 🟣 **OVERRIDDEN** | `DEFAULT_STRATEGY` | Initial target is 34, but full 3Q land reclamation systematically saturates all 38 physical plots. |
| **`"sheep": 6`** | 🔴 **INERT** | `DEFAULT_STRATEGY` | Livestock capital allocator prioritizes cows; 0 sheep are purchased across the entire 720 steps. |
| **`"opening_melons": 9`** | 🔴 **INERT** | `DEFAULT_STRATEGY` | Suppressed by rapid Day 3 Strawberry pivot to eliminate zero-cash insolvency risks. |
| **`"opening_carrots": 2`** | 🔴 **INERT** | `DEFAULT_STRATEGY` | Obsolete opening artifact; suppressed by deterministic Day 1 wheat opening. |

---

## 🔒 Safe Research Rules

1. **`submission.py` is permanently FROZEN (`Control A`)** 🧊.
2. All experimental work happens in `D1_RESEARCH_COPY.py` or `candidates/`.
3. Before evaluating any new candidate, run `experiments/verify_d1_research_copy_parity.py` to confirm exact mathematical parity with `submission.py`.
