# 📜 Phase 16: Animal Staging & Capital Allocation Counterfactual Tournament Report

> **Research Purpose**: Parallel causal counterfactual evaluation of **Animal Staging & Capital Allocation** (delaying Cow #2 and adding Cow #3) across **50 unseen seeds** under strict Kaggle 24-step clearance parity against the protected V4.1 Master Opponent.
> **Objective**: Determine whether staging early livestock purchases unlocks early crop working capital, accelerates strawberry throughput, and breaks the 1200–1400 rating ceiling.

---

## 📊 1. Master Head-to-Head Tournament Results (50 Unseen Seeds, 24-Step Clearance)

| Strategy Arm / Configuration | Mean Wealth ($) | Opponent Wealth ($) | Head-to-Head Win Rate | Milk Revenue ($) | Strawberry Revenue ($) | Cash @ Step 50 ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Control (V4.1 Master Baseline: Cow#1@0, Cow#2@1)** | **$95,222.20** | $94,407.46 | **50.0%** (25W-22L) | $70,419.94 | $93,980.30 | $20.00 |
| **Arm A (Fixed Staging: Cow#2@24, Cow#3@48)** | **$69,907.96** | $135,465.00 | **0.0%** (0W-50L) | $141,407.18 | $114,885.30 | $14.00 |
| **Arm B (Labor & Liquidity Gated: Workers>=4, Cash>=$1.2k)** | **$88,910.72** | $116,536.06 | **0.0%** (0W-50L) | $120,782.46 | $102,696.40 | $13.00 |
| **Arm C (State-Conditioned Dynamic Runway: Cash>=$1.5k)** | **$88,377.86** | $116,760.44 | **0.0%** (0W-50L) | $118,705.82 | $103,465.14 | $13.00 |

---

## 🔍 2. Key Empirical Findings & Causal Insights

1. **Early Working Capital Velocity**:
   - Compares opening liquidity at Step 50 between immediate Cow #2 purchase vs staged acquisition.

2. **Crop & Livestock Revenue Interplay**:
   - Measures whether delaying Cow #2 allows earlier/larger Strawberry seed deployments without hurting lifetime Milk yield.

3. **Competitive Edge vs V4.1 Master**:
   - Tests whether any staged configuration achieves Pareto superiority over standard V4.1 baseline.

---

## 🏛️ Governance, Baseline Protection & Code Integrity

- 🛡️ **V4.1 Master Champion (Ref `55249106`, 1479.8 public / 1714.4 live)**: **100% PROTECTED & UNTOUCHED**.
- 📦 **APEX 3.0 (Ref `55411304`, 1191.0)**: Preserved as historical Kaggle benchmark.
- 🔒 **APEX 3.2 Candidate**: Frozen locally (0 uploads executed).
- 🎯 **Challenger Upload Directive**: Only when a staged animal candidate demonstrates strict Pareto-dominance across all 50 seeds will a formal candidate be considered.
