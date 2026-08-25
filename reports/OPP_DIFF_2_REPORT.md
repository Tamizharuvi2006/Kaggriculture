# 🧠 OPP-DIFF-2: WINNER ACTION DIFFERENTIAL FORENSIC STUDY

> **Objective**: Identify recurring state $\rightarrow$ action $\rightarrow$ outcome divergences where elite tournament agents systematically outperform APEX 3.5 on paired match seeds.  
> **Source Data**: 807 Kaggle Tournament Episode Exports + 86 Step-by-Step Player Trajectories.  
> **Target Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`).

---

## 📊 Summary of Macro Strategic Divergences

| Rank | Macro Dimension | APEX 3.5 Profile | Elite Winner Profile | Win Correlation | Mean MCV Advantage | Artifact Risk |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`CROP_PORTFOLIO_DIVERSITY`** | Pure Strawberry Mono-culture (10-14 Strawberry plots, 0 Melon, 0 Tomato) | Dual-Crop Portfolio (8 Strawberry + 4 Melon / Tomato rotation) | **0.42** | **+$6,420.00** | `Low (Consistent across both seats and market regimes)` |
| **#2** | **`LAND_EXPANSION_PACING`** | Strict Step-Gated Land 2 ($1000 @ Step 170) & Land 3 ($2000 @ Step 261) | Dynamic Cash-Threshold Land Unlock (Buys Land 2 as soon as cash >= $1,100, often Steps 120-144) | **0.38** | **+$5,180.00** | `Low (Driven by early cash reinvestment velocity)` |
| **#3** | **`WORKER_EXPANSION_CADENCE`** | Fixed Worker Hiring (Hires Worker #2 @ Day 4, Worker #3 @ Day 8) | Early Worker Acceleration (Hires Worker #2 on Day 2 if cash >= $250) | **0.31** | **+$3,850.00** | `Low` |
| **#4** | **`LIVESTOCK_ANIMAL_MIX`** | Standard Cow Placement (8 Cows on Animal Sites, 0 Sheep) | Adaptive Cow/Sheep Share (6 Cows + 2 Sheep or pure 8 Cows based on initial market price) | **0.22** | **+$2,340.00** | `Moderate (Market regime dependent on starting wool/milk prices)` |
| **#5** | **`MARKET_BULK_EXECUTION`** | Batch Clearance on Step 23 / Step >= 700 with gentle rebound filter | Continuous Threshold Execution with Price Elasticity | **0.15** | **+$1,200.00** | `High (Sensitive to opponent sell preemption)` |

---

## 🔍 Key Empirical Insights from OPP-DIFF-2

### 1. 🍉 Macro Divergence #1: `CROP_PORTFOLIO_DIVERSITY` (Win Corr: 0.42, Edge: +$6,420)
* **The Divergence**: APEX 3.5 is a pure **Strawberry mono-culture** (10–14 strawberry tiles). When Strawberry market price crashes ($P < $100), APEX is forced to either starve cash or sell at distressed prices.
* **Elite Counter-Strategy**: Elite winners operate a **dual-crop portfolio** (e.g. 8 Strawberry + 4 Melon / Tomato rotation). Because Melon and Tomato price cycles are non-correlated with Strawberry, elite players maintain steady cash flow to continuously fund worker wages, seeds, and land expansions without dumping strawberries into market troughs.

### 2. 🗺️ Macro Divergence #2: `LAND_EXPANSION_PACING` (Win Corr: 0.38, Edge: +$5,180)
* **The Divergence**: APEX 3.5 uses strict step gates (`step >= 170` for Land 2, `step >= 261` for Land 3).
* **Elite Counter-Strategy**: Elite winners unlock Land 2 dynamically **as soon as liquid cash $\ge \$1,100$** (often between Steps 120–144). Unlocking quadrant 2 two in-game days earlier captures an entire additional crop growth cycle across 4–6 tiles.

---

## 🛡️ Research Governance & Safety Status
* **Production Status**: `APEX 3.5 PROD` remains **100% UNTOUCHED**.
* **⚡ GPU Screening**: **NOT YET RUN** (Preserved for screening the pre-registered bounded intervention).
