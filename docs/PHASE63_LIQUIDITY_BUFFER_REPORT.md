# 📜 Phase 63: Cash-Constrained Sale Timing & Dynamic Liquidity Buffer Report

> **Objective**: Evaluate whether a Dual-Regime Liquidity Policy (unconditional immediate liquidation when below SAFE_CASH_BUFFER, and selective market holding only when operating and reinvestment reserves are fully secured) causally increases realized price and final wealth across 50 fresh unseen seeds.

---

## 📊 1. Dynamic Liquidity Buffer Scorecard (50 Fresh Seeds)

| Policy Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Realized Straw Price | Realized Milk Price | Strawberry Volume |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arm A Control** | Current APEX 3.4 Control | **27/50 (54.0%)** | $94,648.26 | **$+57.42** | $147.66/u | $99.91/u | 617.2 units |
| **Arm B Dynamic Buffer** | Unconditional Sale < Safe Buffer; Peak Sale if Surplus | **13/50 (26.0%)** | $92,490.68 | **$-5,260.60** | $171.52/u | $114.02/u | 591.1 units |
| **Arm C Gentle Rebound** | Unconditional Sale < Safe Buffer; Gentle Rebound Exit | **34/50 (68.0%)** | $94,148.66 | **$+843.54** | $159.44/u | $106.29/u | 644.7 units |

---

## 💡 2. Causal Attribution & Evaluation Analysis

1. **Effect of Dynamic Buffer Policy (Arm B vs Control)**:
   - Net Delta: **$-5,260.60**, Win Rate: **26.0%**, Straw Price: **$171.52 vs $147.66**.
2. **Effect of Gentle Rebound Policy (Arm C vs Control)**:
   - Net Delta: **$+843.54**, Win Rate: **68.0%**, Straw Price: **$159.44 vs $147.66**.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
