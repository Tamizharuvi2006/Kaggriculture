# 📌 PROJECT_STATE.md — Kaggle Agriculture 2026

> **Current Verified Best Score**: **$121,973.63** (Official 100-Match Baseline across Seeds 1000–1099)  
> **Repository Location**: `https://github.com/Tamizharuvi2006/Kaggriculture.git`  
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
- **Task Backlog**:
  - [`TODO.md`](file:///D:/kaggle_agriculture_clean/TODO.md)

---

## 🧠 Known Conclusions

1. **SE Expansion Hurts Performance**: Unlocking Quadrant 4 (SE) without task scheduler rewrites drops score from **$122.0k → $108.0k**.
2. **Infinite-Speed Oracle Gives +0.00% Score Change**: Instant movement oracle yields a **perfect +0.00% score change** ($120,716.80 vs $120,716.80).
3. **Transit is NOT the Bottleneck**: Physical movement speed is not what limits farm revenue.
4. **Worker Scheduling is the Primary Bottleneck**: V18's centralized scheduler fails to generate and dispatch high-value work orders, leaving **3.33 workers idle every step** across **10 empty farmland tiles**.

---

## ❓ Open Questions

1. **Why are 3.33 workers idle every step?**
2. **Why do 10 unlocked tiles sit completely unused?**
3. **Which profitable tasks are missing from the work generator?**

---

## 🔬 Completed Research Experiments (1–16)

1. **Research 1 (Crop Alloc Search)**: 15 opening melons provides critical liquidity for early livestock.
2. **Research 2 (Expansion Timing)**: NE Day 5, SW Day 7 optimal unlock.
3. **Research 3 (Animal Mix)**: 12 Cows + 0 Sheep dominates ($120.7k avg).
4. **Research 4 (Occupancy Simulator)**: Early expansion drops land occupancy to 34%.
5. **Research 5 (100 Strategy Monte Carlo)**: Discovered Strategy 15.
6. **Research 6 & 7 (SE Shadow & Cash Flow)**: Day 11 yields +$21,647 harvest burst.
7. **Research 8 & 9 (Strawberry Saturation & Cow Curves)**: 30 Strawberries & 12 Cows are exact labor caps for 75 tiles.
8. **Research 10 (SE Feasibility & Engine Finding)**: Discovered V18 engine hardcodes 75 tiles max (`land_se_day` missing, SE crop tiles filtered out). Proved unlocking SE alone drops score from 122k to 108k due to empty land & cash burn.
9. **Research 11 (Capacity Telemetry)**: Logged 48.66% walking time and 27.99% worker idle time.
10. **Research 12 (Infinite-Speed Oracle)**: Instant movement oracle yielded **+0.00% score change** ($120,716.80 vs $120,716.80). **TRANSIT IS NOT THE BOTTLENECK**.
11. **Research 13 (Scheduler Audit)**: Logged 85.17% of idle worker events occur because `_build_tasks` generates 0 `PLANT` tasks when seed inventory in shed is 0 or crop caps are reached.
12. **Research 14 (Seed Oracle)**: Proved seed inventory restriction is **NOT** the revenue bottleneck. Generating virtual plant tasks dropped score by -$2,146 ($118.5k), and naive seed auto-buy caused total bankruptcy ($158.30).
13. **Research 15 (Profit per Worker-Hour)**: Established action labor efficiency hierarchy: **Strawberries ($73.63/turn) > Melons ($40.53/turn) > Cows ($28.86/turn) > Wheat ($13.51/turn)**.
14. **Research 16 (Cow Replacement Frontier)**: Proved **Cows CANNOT be replaced by crops**. Removing Cows drops score by **-52.8%** ($120.7k → $57.0k) due to liquidity collapse. **12 Cows is the exact mathematical sweet spot** (0 Cows: $57.0k, 4 Cows: $94.2k, 8 Cows: $115.0k, 12 Cows: $120.7k, 16 Cows: $116.2k).

---

## 🎯 Next Engineering Phase

- **Research 17: Integrated Labor & Crop Scheduling Engine** (Optimizing crop placement and dynamic task priorities while preserving 12 Cows).
