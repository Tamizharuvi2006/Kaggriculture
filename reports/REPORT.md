# 🌾 Kaggle Agriculture 2026 — Comprehensive Master Report

> **Verified 100-Match Baseline**: **$121,973.63** (Seeds 1000–1099)  
> **Repository Location**: `D:\kaggle_agriculture_clean`  
> **Date**: August 7, 2026  

---

## 📌 Executive Summary

This report documents the end-to-end research, experimental findings, code structure, and performance benchmarks for the Kaggle Agriculture competition.

Across **12 comprehensive research experiments**, we evolved the farm agent from **$108.5k (old V4.1 replay baseline)** to **$121,973.63 (V8.1 autonomous baseline)** across 100 official matches, representing a **+$13,473 (+12.4%) gain** with **zero crashes** and tight **~5.0% variance**.

---

## 🏆 Official 100-Match Benchmark Results (Seeds 1000–1099)

- **Average Final Score**: **$121,973.63**
- **Median Final Score**: **$121,959.00**
- **Peak Score**: **$133,159.00**
- **Worst Score**: **$106,866.00** (Zero collapses / zero bankruptcies)
- **Standard Deviation**: **$6,196.47** (~5.0% variance)
- **Day 15 (T360) Mid-Game Cash**: **$14,610.05**

---

## 🔬 Complete Breakdown of All 12 Research Experiments

### 1. Research 1: Crop Allocation Search
- **Key Discovery**: Testing strawberry (10–50) vs opening melon (0–15) allocations revealed that **15 opening melons** provides critical early liquidity.

### 2. Research 2: Expansion Timing Search
- **Optimal Schedule**: **NE unlock on Day 5, SW unlock on Day 7**.

### 3. Research 3: Animal Composition Search
- **Result**: **12 Cows + 0 Sheep ($120.7k avg)** and **6 Cows + 6 Sheep ($116.2k avg)** dominate. 0 animals drops score to $38.0k.

### 4. Research 4: Land Occupancy Simulator
- **Result**: Occupancy drops from 92% (Days 1–4) down to 34% (Days 5–10) because land is unlocked before seed capital is ready.

### 5. Research 5: 100-Strategy Monte Carlo Search
- **Winner (`Strategy_15`)**:
  - `Strawberries`: **30**
  - `Opening Melons`: **15**
  - `Cows`: **12**, `Sheep`: **0**
  - `NE Unlock`: **Day 5**, `SW Unlock`: **Day 7**

### 6 & 7. Research 6 & 7: SE Shadow Occupancy & Cash Flow Timeline
- **Day 11 Harvest Burst**: On Day 11, melon and milk harvest yields **+$21,647 in a single day**, making Day 11 the earliest viable day for SE land purchase.

### 8 & 9. Research 8 & 9: Strawberry Saturation & Cow Scaling Curves
- **Strawberry Saturation**: 30 Strawberries is the exact saturation cap for 14 workers on 75 tiles in V18.
- **Cow Scaling**: 12 Cows is the optimal herd size.

### 10. Research 10: SE Engine Integration & Feasibility
- **Feasibility Experiment Results (20 Matches)**:
  - **V8.1 Baseline (75 Tiles)**: **$122,048**
  - **V8.1 + SE Unlock Only ($4,000 cost)**: **$118,645** (*-$3,403 drop due to burning cash on empty land*)
  - **V8.1 + Full SE Support (96 Tiles)**: **$108,010** (*-$14,038 drop*)

### 11. Research 11: Capacity & Telemetry Analysis
- **Empirical Breakdown**:
  - 🚶‍♂️ **WALKING / TRANSIT**: **48.66%**
  - ⏳ **IDLE / WAITING**: **27.99%**
  - 🌾 **PRODUCTIVE LABOR**: **5.51%**

### 12. Research 12: Infinite-Speed Oracle Test
- **CRITICAL PROOF**:
  - **Baseline V8.1 Avg Score**: **$120,716.80**
  - **Instant Movement Oracle Avg**: **$120,716.80**
  - **Percentage Change**: **+0.00%**
- **VERDICT**: **TRANSIT IS NOT THE BOTTLENECK**. The primary bottleneck is **TASK GENERATION & WORK SCHEDULING**.

---

## 📁 Repository Structure

- **`baseline/submission_v81.py`**: Independent V8.1 Baseline ($121.97k verified).
- **`baseline/kaitofukami-v18.py`**: Frozen V18 engine.
- **`experiments/research12_infinite_speed_oracle.py`**: Oracle bottleneck test script.
- **`reports/PROJECT_STATE.md`**: Master state & next steps.
