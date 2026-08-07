# 🌾 Kaggle Agriculture Autonomous AI Agent 2026

> **Current Master Baseline**: `baseline/submission_v83.py` (V8.3 Opponent Supply-Aware Ranker)  
> **Official 100-Match Score**: **$184,404.03** (Seeds 1000–1099, 0 Bankruptcies, $7,666.31 StdDev)  
> **Head-to-Head Win Rate**: **200 / 200 Wins (100.0% Sweep Victory)** vs V5 Agent  
> **Repository**: `https://github.com/Tamizharuvi2006/Kaggriculture.git`

---

## 🏆 Master Submission Status

| Submission Entrypoint | Version Tag | Strategy Config | 100-Match Mean ($) | 100-Match Median ($) | Worst Score ($) | Bankruptcies | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| [`baseline/submission_v83.py`](file:///D:/kaggriculture/baseline/submission_v83.py) | **V8.3** | Cows=13 + Opponent Ranker | **$184,404.03** | **$185,951.00** | **$164,716.00** | **0 / 100** | **MASTER BASELINE** 🥇 |
| [`baseline/submission_v82_cows13.py`](file:///D:/kaggriculture/baseline/submission_v82_cows13.py) | **V8.2** | Cows=13 Control | **$124,753.98** | **$125,877.50** | **$106,552.00** | **0 / 100** | **RETAINED BASELINE** |
| [`baseline/submission_v81_cows12.py`](file:///D:/kaggriculture/baseline/submission_v81_cows12.py) | **V8.1** | Cows=12 Control | **$118,378.43** | **$120,400.00** | **$0.00** | **3 / 100** | **DEPRECATED** |

---

## 📌 Executive Summary

This repository contains the complete research, simulation harness, state-adaptive architecture, and submission entrypoints for the Kaggle Agriculture competition.

Through 19.5 rigorous, empirically validated research experiments, we elevated the farm performance from **$108.5k (old V4.1 baseline)** → **$184,404.03 (V8.3 autonomous baseline)** across 100 official seeds, achieving a significant overall gain with **zero collapses / zero bankruptcies**.

---

## 🏆 Official 100-Match Benchmark Results (Seeds 1000–1099)

- **Median Final Score**: **$125,877.50** (+$4,123.00 gain vs V8.1 Baseline)
- **Peak Score**: **$133,166.00**
- **Worst Score**: **$106,552.00** (Zero collapses / 0 bankruptcies out of 100 matches)
- **Standard Deviation**: **$6,709.16** (69.2% volatility reduction vs V8.1's $21.7k)
- **Day 15 (T360) Mid-Game Cash**: **$14,303.20**

---

## 🧠 Known Conclusions

1. **SE Expansion Hurts Performance**:
   - Unlocking Quadrant 4 (SE) without task scheduler rewrites drops score from **$122.0k → $108.0k**.
   - SE land sits 100% empty while burning $4,000 in land purchase capital.

2. **Infinite-Speed Oracle Gives +0.00% Score Change**:
   - Making worker movement instant (0 turns delay) yields a **perfect +0.00% score change** ($120,716.80 vs $120,716.80).

3. **Transit is NOT the Bottleneck**:
   - Physical movement speed is not what limits farm revenue.

4. **Worker Scheduling is the Primary Bottleneck**:
   - V18's centralized task scheduler fails to generate and dispatch high-value work orders, leaving an average of **3.33 workers idle every step** across 10 empty farmland tiles despite having **$28.7k in cash**.

---

## ❓ Open Questions

1. **Why are 3.33 workers idle every step?**
   - What condition in `_assign_actions()` prevents idle workers from taking on available farm tasks?
2. **Why do 10 unlocked tiles sit completely unused?**
   - Is crop target logic capping crop planting artificially at 30 strawberries?
3. **Which profitable tasks are missing?**
   - What high-ROI crop/animal maintenance tasks should be added to the scheduler?

---

## 📂 File Map & Code Locations

| File Path | Description / Role |
| :--- | :--- |
| **`baseline/submission_v81.py`** | **FROZEN Official Submission**. Independent V8.1 entrypoint ($121.97k 100-match baseline). |
| **`baseline/kaitofukami-v18.py`** | **Frozen Underlying Engine**. Kept 100% untouched. |
| **`experiments/submission_v82_exp.py`** | **V8.2 Experimental Branch**. Integrates `world_state.py` telemetry and adaptive gating. |
| **`experiments/world_state.py`** | Real-time farm state evaluator (money, feed runway, occupancy ratio, emergency flags). |
| **`experiments/adaptive_engine.py`** | Dynamic strategy controller & emergency feed safety intervention logic. |
| **`experiments/research10_se_feasibility.py`** | SE Quadrant 4 feasibility patch & benchmark script. |
| **`experiments/research11_capacity_bottleneck.py`** | Detailed worker task, transit, idle, and capacity bottleneck analyzer. |
| **`experiments/research12_infinite_speed_oracle.py`** | Infinite-speed oracle test script. |
| **`benchmarks/strategy_search.py`** | Parallel strategy search harness (`ProcessPoolExecutor`, 8 CPU workers). |
| **`reports/REPORT.md`** | Master research report covering Research 1 through 12. |
| **`reports/PROJECT_STATE.md`** | Master project state & open roadmap questions. |
| **`TODO.md`** | Research 13 Scheduler Audit task definition. |

---

## 🔬 Summary of All 12 Research Experiments

- **Research 1 (Crop Alloc Search)**: 15 opening melons provides critical early liquidity.
- **Research 2 (Expansion Timing Search)**: NE Day 5, SW Day 7 optimal unlock.
- **Research 3 (Animal Composition Search)**: 12 Cows + 0 Sheep dominates ($120.7k avg).
- **Research 4 (Land Occupancy Simulator)**: Early land expansion drops occupancy to 34%.
- **Research 5 (100-Strategy Monte Carlo Search)**: Discovered Strategy 15.
- **Research 6 & 7 (SE Shadow & Cash Flow)**: Day 11 yields +$21,647 harvest burst.
- **Research 8 & 9 (Strawberry Saturation & Cow Curves)**: 30 Strawberries & 12 Cows are exact labor caps for 75 tiles.
- **Research 10 (SE Feasibility & Engine Finding)**: Discovered V18 engine hardcodes 75 tiles max (`land_se_day` missing, SE crop tiles filtered out). Proved unlocking SE alone drops score from 122k to 108k due to empty land & cash burn.
- **Research 11 (Capacity Telemetry)**: Logged 48.66% walking time and 27.99% worker idle time.
- **Research 12 (Infinite-Speed Oracle)**: Instant movement oracle yielded **+0.00% score change** ($120,716.80 vs $120,716.80). Proved transit is NOT the bottleneck and task scheduling is the primary bottleneck.
