# 📌 PROJECT_STATE.md — Kaggle Agriculture 2026

> **Current Verified Best Score**: **$121,973.63** (Official 100-Match Baseline across Seeds 1000–1099)  
> **Last Updated**: August 7, 2026  

---

## 🏛️ Repository Layout & Architecture

- **Baseline Submission**: [`baseline/submission_v81.py`](file:///D:/kaggle_agriculture_clean/baseline/submission_v81.py) (Independent V8.1 entrypoint)
- **Baseline Engine**: [`baseline/kaitofukami-v18.py`](file:///D:/kaggle_agriculture_clean/baseline/kaitofukami-v18.py) (Frozen underlying engine)
- **Experimental Files**:
  - [`experiments/world_state.py`](file:///D:/kaggle_agriculture_clean/experiments/world_state.py)
  - [`experiments/adaptive_engine.py`](file:///D:/kaggle_agriculture_clean/experiments/adaptive_engine.py)
  - [`experiments/submission_v82_exp.py`](file:///D:/kaggle_agriculture_clean/experiments/submission_v82_exp.py)
  - [`experiments/research10_se_feasibility.py`](file:///D:/kaggle_agriculture_clean/experiments/research10_se_feasibility.py)
  - [`experiments/research11_capacity_bottleneck.py`](file:///D:/kaggle_agriculture_clean/experiments/research11_capacity_bottleneck.py)
  - [`experiments/research12_infinite_speed_oracle.py`](file:///D:/kaggle_agriculture_clean/experiments/research12_infinite_speed_oracle.py)
- **Master Reports**:
  - [`reports/REPORT.md`](file:///D:/kaggle_agriculture_clean/reports/REPORT.md)
  - [`reports/PROJECT_STATE.md`](file:///D:/kaggle_agriculture_clean/reports/PROJECT_STATE.md)

---

## 🔬 Completed Research Experiments (1–12)

1. **Research 1 (Crop Alloc Search)**: 15 opening melons provides critical liquidity for early livestock.
2. **Research 2 (Expansion Timing)**: NE Day 5, SW Day 7 optimal unlock.
3. **Research 3 (Animal Mix)**: 12 Cows + 0 Sheep dominates ($120.7k avg).
4. **Research 4 (Occupancy Simulator)**: Early expansion drops land occupancy to 34%.
5. **Research 5 (100 Strategy Monte Carlo)**: Discovered Strategy 15.
6. **Research 6 & 7 (SE Shadow & Cash Flow)**: Day 11 yields +$21,647 harvest burst.
7. **Research 8 & 9 (Strawberry Saturation & Cow Curves)**: 30 Strawberries & 12 Cows are exact labor caps for 75 tiles.
8. **Research 10 (SE Feasibility & Engine Finding)**: Discovered V18 engine hardcodes 75 tiles max (`land_se_day` missing, SE crop tiles filtered out). Proved unlocking SE alone drops score from 122k to 108k due to empty land & cash burn.
9. **Research 11 (Capacity Telemetry)**: Logged 48.66% walking time and 27.99% worker idle time.
10. **Research 12 (Infinite-Speed Oracle)**: **CRITICAL DISCOVERY**. Instant movement oracle yielded **+0.00% score change** ($120,716.80 vs $120,716.80). **TRANSIT IS NOT THE BOTTLENECK**.

---

## 💡 The Ultimate Bottleneck Verdict

> **PRIMARY BOTTLENECK = TASK GENERATION & WORK SCHEDULING**

- Movement speed has **zero impact (+0.00%)** on final score.
- Workers are walking and sitting idle (3.33 workers idle/step across 10 empty tiles) because V18's centralized scheduler **fails to generate and dispatch high-value work orders**.

---

## ❌ Failed Ideas & Negative Results

- **Movement Speed / Pathfinding Optimization**: Instant movement yields +0.00% improvement.
- **Naive SE Expansion**: Unlocking SE without task scheduler rewrite drops score from **$122.0k → $108.0k**.
- **Skewed Sheep Herds**: Sheep-heavy builds drop score to $38.0k (bankruptcy).

---

## 🎯 Next Three Experiments to Execute

1. **Autonomous Dynamic Task Dispatcher**: Replace static `_assign_actions()` queue with real-time value-density task generation (assigning idle workers to plant/harvest high-ROI crops dynamically).
2. **Dynamic Crop Target Scaling**: Allow crop planner to scale strawberries beyond 30 tiles dynamically based on available worker bandwidth.
3. **96-Tile SE Expansion with Dynamic Work Allocation**: Unlock SE on Day 11+ and dispatch dynamic task queues across all 96 tiles (Target: 140k–200k).
