# 🧠 RESEARCH COUNCIL CYCLE #8: META-AUDIT & LIQUIDITY MANAGEMENT QUEUE

> **Audit Scope**: 807 Tournament Matches, 46 Ladder Loss Seeds, 86 Trajectories, and Complete `EXP-0113` through `EXP-0142` Ledger.  
> **Strategic Insight**: Shifting to **Liquidity Management & Reactive Market Mechanics** (`cash_reserve`, `interference_targeted_sort`, `interference_wheat_squeeze`) which actively modulate every purchase order in `_market_orders()`.  
> **Permanently Excluded**: All 18 closed/invalid families.

---

## 📊 1. Top 5 Ranked Opportunities

| Rank | Experiment ID | Hypothesis Archetype | Verified Baseline Occurrence | Causal Mechanism | Expected MCV Lift | Observability | GPU Screening? |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`EXP-0144`** | **`DYNAMIC_CASH_RESERVE_PHASE_SCALING`** | `cash_reserve = 150` static floor in `_market_orders()`. | Scaling reserve to $0 in Days 0–4 unlocks early working capital for seeds/fertilizer. | **`+$800 to +$1,600`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#2** | **`EXP-0143`** | **`TARGETED_MARKET_INTERFERENCE_SORTING`** | `interference_targeted_sort = False`. | Sells commodities visible in opponent's ripening pipeline before opponent can sell. | **`+$500 to +$1,100`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#3** | **`EXP-0146`** | **`DYNAMIC_WHEAT_SQUEEZE_ON_HERD_EXPANSION`** | `interference_wheat_squeeze = False`. | Drives up feed price on large opponent herds (8+ cows). | **`+$400 to +$900`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#4** | **`EXP-0147`** | **`EARLY_LIQUIDITY_FLOOR_SCALING`** | `early_liquidity_floor = 0`. | Tunes liquidity floor across [0, 50, 100, 150] to smooth cashflow. | **`+$350 to +$750`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#5** | **`EXP-0145`** | **`INTERFERENCE_EXPOSURE_THRESHOLD_TUNING`** | `interference_min_exposure = 0.50`. | Tunes exposure trigger sensitivity in [0.25, 0.35, 0.50, 0.65]. | **`+$300 to +$700`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |

---

## 🔍 2. Deep Dive: Top Recommended Primary Target (`EXP-0144`)

```
========================================================================================================
[EXP-0144: DYNAMIC CASH RESERVE PHASE SCALING]
========================================================================================================
  • Baseline Setting             : STRATEGY['cash_reserve'] = 150 (Static across all 720 steps)
  • The Active Runtime Problem   : In _market_orders(), if money - cost < cash_reserve (150), 
                                   any market purchase is BLOCKED.
                                   In Days 0-4, farm cash is often between $60 and $140. 
                                   The bot has sufficient cash to buy fertilizer ($10) or seeds ($100), 
                                   but the static $150 reserve blocks the purchase!
  • Proposed Optimization        : Scale cash reserve by game phase:
                                   - Days 0 – 4 : $0   (Maximize initial working capital velocity)
                                   - Days 5 – 20: $150 (Standard operational safety buffer)
                                   - Days 21 – 30: $0  (Zero terminal cash lock)
  • Expected Impact              : Prevents blocked fertilizer and seed purchases in early game, 
                                   accelerating early strawberry revenue by +$800 to +$1,600 MCV.
========================================================================================================
```

---

## ⚖️ 3. Governance Status & Research Recommendation
1. `EXP-0144` operates directly inside the **active gating logic of `_market_orders()`**, which is evaluated on every single step.
2. It satisfies all 6 criteria: **Real Baseline Occurrence**, **Real Causal Mechanism**, **Competitive Win Condition**, **100% Legal Internal State**, **Physical Lifecycle Safety**, and **Not Already Falsified**.
3. The Research Council recommends **`EXP-0144`** as the next primary research target.
