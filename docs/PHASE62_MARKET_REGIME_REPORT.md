# 📜 Phase 62: Price-Velocity Market Regime Counterfactual Report

> **Objective**: Test whether momentum-aware market overlays (suppressing VALLEY_CRASH sales and accelerating PEAK liquidations) causally increase realized prices and wealth across 50 fresh unseen seeds.

---

## 📊 1. Price-Velocity Regime Scorecard (50 Fresh Seeds)

| Policy Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Realized Straw Price | Realized Milk Price | Peak Sale % | Crash Sale % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arm A Control** | Current APEX 3.4 Control | **27/50 (54.0%)** | $94,648.26 | **$+57.42** | $147.66/u | $99.91/u | 67.1% | 21.7% |
| **Arm B Crash Avoidance** | Suppress VALLEY_CRASH (P<135/110, v<=0) | **9/50 (18.0%)** | $92,628.82 | **$-6,640.32** | $170.14/u | $113.70/u | 82.0% | 3.4% |
| **Arm C Crash And Peak** | Suppress Crash + Accelerate Peak Sales | **11/50 (22.0%)** | $92,421.22 | **$-5,177.58** | $171.30/u | $113.56/u | 83.3% | 3.0% |

---

## 💡 2. Causal Attribution & Evaluation Analysis

1. **Effect of Crash-Dumping Avoidance (Arm B vs Control)**:
   - Net Delta: **$-6,640.32**, Win Rate: **18.0%**, Crash Sale Rate: **3.4% vs 21.7%**.
2. **Effect of Peak Sale Acceleration (Arm C vs Control)**:
   - Net Delta: **$-5,177.58**, Win Rate: **22.0%**, Peak Sale Rate: **83.3% vs 67.1%**.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
