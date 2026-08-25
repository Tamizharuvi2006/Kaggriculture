# 🧠 RESEARCH COUNCIL CYCLE #9: META-AUDIT & ACTIVE RUNTIME QUEUE

> **Audit Scope**: 807 Tournament Matches, 46 Ladder Loss Seeds, 86 Trajectories, and Complete `EXP-0113` through `EXP-0144` Ledger.  
> **Strategic Focus**: Target the active runtime layers inside `agent()`:
> 1. `_apply_market_interference()` (Evaluated on every step in tournament play).
> 2. `_safe_wheat_squeeze()` (Active feed-denial module in Days 8–24).
> 3. `safe_buffer` calibration in `agent()` (Regulates liquidity execution in Quadrants 1, 2, 3).  
> **Permanently Excluded**: All 19 closed/invalid families.

---

## 📊 1. Top 5 Ranked Opportunities

| Rank | Experiment ID | Hypothesis Archetype | Verified Baseline Occurrence | Causal Mechanism | Expected MCV Lift | Observability | GPU Screening? |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`EXP-0143`** | **`TARGETED_MARKET_INTERFERENCE_SORTING`** | `interference_targeted_sort = False` in `_apply_market_interference()`. | Sequences sell orders by `_interference_value` to hit order book ahead of rival's ripening crops. | **`+$600 to +$1,400`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#2** | **`EXP-0146`** | **`DYNAMIC_WHEAT_FEED_PRICE_SQUEEZE`** | `interference_wheat_squeeze = False` in `_safe_wheat_squeeze()`. | Drives up feed price on large opponent herds (8+ cows) in Days 8–24. | **`+$400 to +$900`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#3** | **`EXP-0147`** | **`SAFE_BUFFER_QUADRANT_2_CALIBRATION`** | `safe_buffer = 2200` in Quadrant 2. | Calibrates liquidity threshold in [$1600, $1800, $2000, $2200] to capture peak prices. | **`+$350 to +$800`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#4** | **`EXP-0148`** | **`INTERFERENCE_MIN_EXPOSURE_CALIBRATION`** | `interference_min_exposure = 0.50`. | Tunes exposure threshold in [0.20, 0.35, 0.50, 0.65]. | **`+$300 to +$700`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#5** | **`EXP-0149`** | **`GENTLE_REBOUND_MOMENTUM_FILTER_THRESHOLD`** | `p_straw >= 140.0` selling trigger. | Calibrates peak strawberry selling threshold across [130, 135, 140, 145]. | **`+$250 to +$600`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |

---

## 🔍 2. Deep Dive: Top Recommended Primary Target (`EXP-0143`)

```
========================================================================================================
[EXP-0143: TARGETED MARKET INTERFERENCE SORTING]
========================================================================================================
  • Baseline Setting             : STRATEGY['interference_targeted_sort'] = False
  • Active Execution Path        : Evaluated on EVERY SINGLE STEP inside _apply_market_interference()
  • Verified Causal Mechanism    : Currently, APEX 3.5 sells products in default schedule index order.
                                   When interference_targeted_sort = True:
                                   Orders are sorted by _interference_value(exposure * price * qty).
                                   The product with the highest opponent pipeline collision is sold FIRST,
                                   depressing the shared market clearing price immediately before the 
                                   opponent can liquidate their ripening harvest!
  • Competitive Separation       : Squeezes $400 to $900 in revenue from the opponent in contested crop games.
========================================================================================================
```

---

## ⚖️ 3. Governance Status & Research Recommendation
1. `EXP-0143` operates inside an **active, step-by-step runtime hook (`_apply_market_interference`)** that is executed on 100% of tournament steps.
2. It uses **100% legally observable public opponent tile state** (`_opponent_pipeline(obs)`).
3. The Research Council recommends **`EXP-0143`** as the next primary research target.
