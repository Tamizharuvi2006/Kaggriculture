# 🌾 Kaggle Agriculture 2026 — Ultimate Master Research & Architecture README

> **Status**: **Official 100-Match Baseline Verified: $121,973.63** (Seeds 1000–1099)  
> **Repository Location**: `D:\kaggle_agriculture`  
> **Last Updated**: August 7, 2026  

---

## 📌 Executive Summary

This repository contains the complete research, simulation harness, state-adaptive architecture, and submission entrypoints for the Kaggle Agriculture competition.

Through 11 rigorous, empirically validated research experiments, we elevated the farm performance from **$108.5k (old V4.1 replay baseline)** to **$121,973.63 (V8.1 autonomous baseline)** across 100 official seeds, representing a **+$13,473 (+12.4%) gain** with **zero crashes** and tight **~5.0% variance**.

---

## 🏆 Official 100-Match Benchmark Results (Seeds 1000–1099)

- **Average Final Score**: **$121,973.63**
- **Median Final Score**: **$121,959.00**
- **Peak Score**: **$133,159.00**
- **Worst Score**: **$106,866.00** (Zero collapses / zero bankruptcies)
- **Standard Deviation**: **$6,196.47** (~5.0% variance)
- **Day 15 (T360) Mid-Game Cash**: **$14,610.05**

---

## 📂 File Map & Code Locations

| File Path | Description / Role |
| :--- | :--- |
| **[`submission.py`](file:///D:/kaggle_agriculture/submission.py)** | **FROZEN Official Submission**. Contains V8.1 parameter overrides on `kaitofukami-v18.py` ($121.97k 100-match baseline). |
| **[`submission_v82_exp.py`](file:///D:/kaggle_agriculture/submission_v82_exp.py)** | **V8.2 Experimental Branch**. Integrates `world_state.py` telemetry and adaptive gating. |
| **[`world_state.py`](file:///D:/kaggle_agriculture/world_state.py)** | Real-time farm state evaluator (money, feed runway, occupancy ratio, labor saturation, emergency flags). |
| **[`adaptive_engine.py`](file:///D:/kaggle_agriculture/adaptive_engine.py)** | Dynamic strategy controller & emergency feed safety intervention logic. |
| **[`strategy_search.py`](file:///D:/kaggle_agriculture/strategy_search.py)** | Parallel strategy search harness (`ProcessPoolExecutor`, 8 CPU workers). |
| **[`run_official_100_matches.py`](file:///D:/kaggle_agriculture/run_official_100_matches.py)** | Benchmark runner for 100 official matches. |
| **[`benchmark_v82_phased.py`](file:///D:/kaggle_agriculture/benchmark_v82_phased.py)** | Phased validation script for testing V8.2 experimental modifications. |
| **[`research10_se_feasibility.py`](file:///D:/kaggle_agriculture/research10_se_feasibility.py)** | SE Quadrant 4 feasibility patch & benchmark script. |
| **[`research11_capacity_bottleneck.py`](file:///D:/kaggle_agriculture/research11_capacity_bottleneck.py)** | Detailed worker task, transit, idle, and capacity bottleneck analyzer. |
| **[`README.md`](file:///D:/kaggle_agriculture/README.md)** | **This Document**. |

---

## 🔬 Complete Summary of All 11 Research Experiments

### 🧪 Research 1: Crop Allocation Search
- **Discovery**: Testing strawberry (10–50) vs opening melon (0–15) allocations revealed that **15 opening melons** provides critical early liquidity.
- **Key Insight**: Wheat/Melon sales before Day 10 fund livestock acquisition without debt.

### 🧪 Research 2: Expansion Timing Search
- **Discovery**: Tested NE/SW quadrant unlock days `[2, 3, 5, 7, 10, 14, 99]`.
- **Optimal Schedule**: **NE unlock on Day 5, SW unlock on Day 7**. Unlocking earlier starves seed capital; unlocking later delays strawberry production.

### 🧪 Research 3: Animal Composition Search
- **Discovery**: Evaluated 14 livestock combinations (cows vs sheep).
- **Result**: **12 Cows + 0 Sheep ($120.7k avg)** and **6 Cows + 6 Sheep ($116.2k avg)** dominate. Skewed sheep herds drop score. 0 animals drops score to $38.0k (bankruptcy).

### 🧪 Research 4: Land Occupancy Simulator
- **Discovery**: Tracked tile occupancy day-by-day across 75 tiles.
- **Result**: Occupancy drops from 92% (Days 1–4) down to 34% (Days 5–10) because land is unlocked before seed capital is ready.

### 🧪 Research 5: 100-Strategy Monte Carlo Search
- **Discovery**: Screened 100 randomized strategy tuples across 500 matches.
- **Winner (`Strategy_15`)**:
  - `Strawberries`: **30**
  - `Opening Melons`: **15**
  - `Cows`: **12**, `Sheep`: **0**
  - `NE Unlock`: **Day 5**, `SW Unlock`: **Day 7**

### 🧪 Research 6 & 7: SE Shadow Occupancy & Cash Flow Timeline
- **Discovery**: Analyzed cash balance day-by-day. Pre-Day 11 cash balance is $11–$746 (unaffordable for $4,000 SE unlock).
- **Day 11 Harvest Burst**: On Day 11, melon and milk harvest yields **+$21,647 in a single day**, making Day 11 the earliest viable day for SE land purchase.

### 🧪 Research 8 & 9: Strawberry Saturation & Cow Scaling Curves
- **Discovery**:
  - **Strawberry Saturation**: 30 Strawberries is the exact saturation cap for 14 workers on 75 tiles (35+ strawberries causes rotted crops and score drops).
  - **Cow Scaling**: 12 Cows is the optimal herd size; 14 cows causes feed exhaustion.

### 🧪 Research 10: SE Engine Integration & Feasibility
- **Crucial Code Finding**:
  1. `kaitofukami-v18.py` has **no `land_se_day` handler** in `_market_orders()`.
  2. `_build_crop_plan()` explicitly filtered out SE tiles `(x>=5, y>=5)` from candidate crop sites.
- **Feasibility Experiment Results (20 Matches)**:
  - **V8.1 Baseline (75 Tiles)**: **$122,048**
  - **V8.1 + SE Unlock Only ($4,000 cost)**: **$118,645** (*-$3,403 drop due to burning cash on empty land*)
  - **V8.1 + Full SE Support (96 Tiles)**: **$108,010** (*-$14,038 drop*)
- **Root Cause**: V8.1 specifies 30 strawberries. Distance sorting fills NW/NE/SW first. Zero crops reach SE, leaving SE 100% empty while burning $4,000 land cost and adding pathfinding overhead.

### 🧪 Research 11: Capacity & Worker Time Bottleneck Analysis
- **Empirical Worker Time Allocation**:
  - 🚶‍♂️ **WALKING / TRANSIT**: **48.66%** of total worker-hours!
  - ⏳ **IDLE / WAITING**: **27.99%** of total worker-hours (average 3.33 idle workers/step)!
  - 🔄 **OTHER / SETUP**: **16.21%**
  - 🌾 **HARVESTING**: **2.42%**
  - 🐄 **HERDING / ANIMAL CARE**: **2.24%**
  - 🌱 **PLANTING**: **0.85%**
- **#1 Primary Bottleneck**: **LOGISTICS & TRANSIT TIME OVERHEAD (48.66%)**.
  Workers spend half their lives walking back and forth to the shed `(4, 4)`. Actual productive work (harvesting + planting + herding) takes only **5.51%** of total time. Adding SE tiles expands walking distance to `(9, 9)`, pushing transit time over 65% and causing crops to rot.

---

## 🛠️ Strategy 15 Parameter Configuration (V8.1 Baseline)

```python
STRATEGY_15_OVERRIDES = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}
```

---

## 🚀 Future Roadmap to 200k

1. **Reduce Transit Overhead (48.66% -> <25%)**:
   - Implement localized worker task batching (workers harvest multi-tile clusters before walking back to shed).
2. **Eliminate Idle Worker Time (27.99% -> <5%)**:
   - Dispatch workers dynamically as soon as they become free rather than waiting for global scheduling steps.
3. **Profitable 96-Tile SE Expansion**:
   - Unlock SE on Day 11+ (post-+$21.6k harvest burst).
   - Scale strawberries from 30 -> 45–50 with localized worker clusters to keep SE occupancy >80%.
