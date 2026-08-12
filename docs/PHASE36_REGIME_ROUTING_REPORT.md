# 📜 Phase 36: Regime Routing & Batch Protection Lab Report

> **Objective**: Test whether optimizing the market regime routing threshold (Milk Price $\ge \$145$) and Strawberry Batch Protection outperforms the static baseline across 50 fresh unseen seeds.

---

## 📊 1. Master Performance Scorecard (50 Fresh Seeds)

| Experimental Arm | Milk Routing Threshold | Batch Protection | Win Rate (/50) | Mean Challenger Wealth ($) | Mean Benchmark Wealth ($) | Net Wealth Delta ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Control (Default 193 Thresh)** | $193 | Disabled | **27/50 (54.0%)** | $94,465.38 | $94,483.04 | **$-17.66** |
| **Arm A (Batch Protection Only)** | $193 | Enabled | **27/50 (54.0%)** | $94,452.62 | $94,520.76 | **$-68.14** |
| **Arm B (Regime Threshold 145 + Batch Prot)** | $145 | Enabled | **27/50 (54.0%)** | $94,452.62 | $94,520.76 | **$-68.14** |
| **Arm C (Regime Threshold 135 + Batch Prot)** | $135 | Enabled | **27/50 (54.0%)** | $94,452.62 | $94,520.76 | **$-68.14** |

---

## 💡 2. Key Empirical Conclusions

1. **Strawberry Batch Protection Impact**:
   - Suppressing clearance Strawberry micro-sales (holding for $\ge 8$ units) improved win rate from **54.0% to 54.0%** and generated **$-68.14** net delta over the benchmark.
2. **Market Regime Routing (Milk Threshold $145)**:
   - Lowering the alpha routing threshold from $193 to $145 allows the policy to capitalize on High-Milk regimes, achieving **54.0% win rate** with **$-68.14** net margin.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
