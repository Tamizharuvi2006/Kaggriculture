# 📜 Phase 107: Fixed vs Dynamic Core Engine Benchmark Report

> **Objective**: Determine whether `submission.py` (V4.1, rated 1479.8) uses a fundamentally
> different engine path than APEX 3.6, and measure the performance difference.

> **Total Episodes**: 462 full 720-step episodes across 5 cohorts, 2 arms each.
> **Multiprocessing**: 8 worker processes.

---

## 📊 1. Master Comparison Table

| Cohort | Arm | Episodes | Win Rate | Mean Wealth | Mean Opp Wealth | Margin | L2 Step | L3 Step | Straw Sold | Milk Sold | Sell Orders | PASS Actions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Seat 0 Fresh** | **FIXED** | 50 | **78.0%** (39/50) | $95,869.32 | $94,056.74 | $+1,812.58 | 170.0 | 261.0 | 643.2 | 661.5 | 479.6 | 377.0 |
| **Seat 0 Fresh** | **DYNAMIC** | 50 | **0.0%** (0/50) | $60,863.08 | $132,796.46 | $-71,933.38 | 237.8 | 266.0 | 202.5 | 102.9 | 88.2 | 2218.6 |
| **Seat 1 Fresh** | **FIXED** | 50 | **86.0%** (43/50) | $95,143.68 | $94,194.58 | $+949.10 | 170.0 | 261.0 | 641.1 | 690.1 | 485.5 | 377.0 |
| **Seat 1 Fresh** | **DYNAMIC** | 50 | **0.0%** (0/50) | $61,010.48 | $133,499.90 | $-72,489.42 | 237.8 | 266.0 | 202.3 | 104.0 | 88.4 | 2213.3 |
| **Parity Losses** | **FIXED** | 11 | **90.9%** (10/11) | $83,754.18 | $81,837.27 | $+1,916.91 | 170.0 | 261.0 | 651.5 | 649.1 | 480.9 | 377.0 |
| **Parity Losses** | **DYNAMIC** | 11 | **0.0%** (0/11) | $48,248.82 | $114,334.18 | $-66,085.36 | 240.0 | 266.0 | 195.9 | 99.3 | 87.5 | 2268.9 |
| **Champion Seeds** | **FIXED** | 20 | **75.0%** (15/20) | $95,793.90 | $91,954.40 | $+3,839.50 | 170.0 | 261.0 | 654.2 | 676.7 | 482.8 | 377.0 |
| **Champion Seeds** | **DYNAMIC** | 20 | **0.0%** (0/20) | $57,622.30 | $127,985.75 | $-70,363.45 | 236.7 | 266.0 | 201.6 | 97.8 | 87.0 | 2236.9 |
| **Mixed Field** | **FIXED** | 100 | **81.0%** (81/100) | $91,577.99 | $90,245.06 | $+1,332.93 | 170.0 | 261.0 | 638.3 | 671.8 | 481.3 | 377.0 |
| **Mixed Field** | **DYNAMIC** | 100 | **0.0%** (0/100) | $60,529.19 | $132,219.69 | $-71,690.50 | 235.8 | 266.0 | 200.9 | 105.0 | 88.5 | 2232.3 |

---

## 📊 2. Per-Cohort DYNAMIC vs FIXED Delta Summary

| Cohort | FIXED WR | DYNAMIC WR | WR Delta | FIXED Wealth | DYNAMIC Wealth | Wealth Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Seat 0 Fresh** | 78.0% | 0.0% | **-78.0%** | $95,869.32 | $60,863.08 | **$-35,006.24** |
| **Seat 1 Fresh** | 86.0% | 0.0% | **-86.0%** | $95,143.68 | $61,010.48 | **$-34,133.20** |
| **Parity Losses** | 90.9% | 0.0% | **-90.9%** | $83,754.18 | $48,248.82 | **$-35,505.36** |
| **Champion Seeds** | 75.0% | 0.0% | **-75.0%** | $95,793.90 | $57,622.30 | **$-38,171.60** |
| **Mixed Field** | 81.0% | 0.0% | **-81.0%** | $91,577.99 | $60,529.19 | **$-31,048.80** |

---

## 📊 3. Head-to-Head Seed Comparison (Mixed Field)

Counting seeds where DYNAMIC wins vs FIXED wins vs ties:

- **DYNAMIC wins more wealth**: 1 seeds
- **FIXED wins more wealth**: 49 seeds
- **Tied**: 0 seeds

---

## 🏛️ Governance

- 🛡️ **No code was modified**. This is a pure read-only benchmark.
- 🛡️ **APEX 3.5 (`Ref 55483322`) remains active on Kaggle**.
- 🛡️ **No submission, no git push.**