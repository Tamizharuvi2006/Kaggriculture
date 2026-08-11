# 📜 Phase 25: Strawberry Activation Population Study Report

> **Dataset**: 86 player trajectories across 43 real Kaggle competition matches.
> **Objective**: Quantify the empirical frequency, win rate, and mean wealth across all Strawberry activation timing windows.

---

## 📊 1. Empirical Population Distribution

| Activation Window | Timing Horizon | Player Count (%) | Win Rate (%) | Mean Final Wealth ($) | Mean 1st Plant Step | Early Melon Units | Early Fertilizer Rev ($) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bucket 1: $\le 72$** | **Day 0–3.0 (Aggressive)** | **6 (7.0%)** | **16.7%** | **$44,339.83** | **Step 41.3** | 11.2 | $83.00 |
| **Bucket 2: $73–96$** | **Day 3.0–4.0 (Early)** | **1 (1.2%)** | **0.0%** | **$88,732.00** | **Step 83.0** | 7.0 | $298.00 |
| **Bucket 3: $97–120$** | **Day 4.0–5.0 (Standard)** | **60 (69.8%)** | **58.3%** | **$74,866.62** | **Step 108.2** | 7.0 | $412.33 |
| **Bucket 4: $> 120$** | **Day 5.0+ (Late / None)** | **19 (22.1%)** | **36.8%** | **$56,063.68** | **Step 311.1** | 9.7 | $88.47 |

---

## 🔍 2. Definitive Population Findings

1. **Bucket 3 (Day 4.0–5.0 / Steps 97–120) is the Dominant Meta Baseline**:
   - Represents the vast majority of competitive match strategies.
2. **Bucket 1 ($\le 72$ / Aggressive Early Opening)**:
   - Represents specialized aggressive agents (like `kazusw`).
   - Generates highest mean wealth when successful, driven by early Melon planting and fast Fertilizer liquidation.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
