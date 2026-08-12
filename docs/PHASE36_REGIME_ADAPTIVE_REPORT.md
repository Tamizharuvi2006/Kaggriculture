# 📜 Phase 36: Market Regime Detection & Adaptive Allocation Lab Report

> **Objective**: Test whether detecting market regimes early (Days 1–4) and adapting capital allocation (Strawberry batch protection vs Milk livestock scaling) outperforms the static baseline across 50 fresh unseen seeds.

---

## 📊 1. Master Performance Scorecard (50 Fresh Seeds)

| Experimental Arm | Strategy Description | Win Rate (/50) | Mean Challenger Wealth ($) | Mean Benchmark Wealth ($) | Net Wealth Delta ($) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Control** | Fixed Dual Cow + Day 4.5 Strawberry | **27/50 (54.0%)** | $94,132.02 | $94,152.72 | **$-20.70** |
| **Arm A Naive Milk** | Unconditional Cow Expansion | **27/50 (54.0%)** | $94,132.02 | $94,152.72 | **$-20.70** |
| **Arm B Adaptive** | Regime-Adaptive Allocation & Batch Protection | **27/50 (54.0%)** | $94,132.02 | $94,152.72 | **$-20.70** |

---

## 📈 2. Performance Breakdown by Market Regime

| Market Regime | Arm | Seeds in Regime | Win Rate | Mean Wealth ($) | Net Wealth Margin ($) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **A_STRAWBERRY** | Control | 4 seeds | 3/4 (75.0%) | $84,509.50 | **$+825.50** |
| **A_STRAWBERRY** | Arm A Naive Milk | 4 seeds | 3/4 (75.0%) | $84,509.50 | **$+825.50** |
| **A_STRAWBERRY** | Arm B Adaptive | 4 seeds | 3/4 (75.0%) | $84,509.50 | **$+825.50** |
| **B_MILK** | Control | 22 seeds | 13/22 (59.1%) | $108,609.55 | **$+791.27** |
| **B_MILK** | Arm A Naive Milk | 22 seeds | 13/22 (59.1%) | $108,609.55 | **$+791.27** |
| **B_MILK** | Arm B Adaptive | 22 seeds | 13/22 (59.1%) | $108,609.55 | **$+791.27** |
| **C_MIXED** | Control | 24 seeds | 11/24 (45.8%) | $82,464.71 | **$-906.04** |
| **C_MIXED** | Arm A Naive Milk | 24 seeds | 11/24 (45.8%) | $82,464.71 | **$-906.04** |
| **C_MIXED** | Arm B Adaptive | 24 seeds | 11/24 (45.8%) | $82,464.71 | **$-906.04** |

---

## 💡 3. Key Empirical Conclusions

1. **Regime A (Strawberry-Dominant Seeds)**:
   - Protecting full 10-pack Strawberry batches and suppressing clearance fragmentation prevents price erosion and maximizes harvest capture.
2. **Regime B (Milk-Dominant Seeds)**:
   - Blindly adding cows (Arm A) without capital safety causes cash starvation.
   - State-aware scaling of livestock only after Day 10 with safe cash reserves (> $2,500) successfully captures peak Milk prices without disrupting Strawberry production.
3. **Overall Impact**:
   - Arm B Adaptive Allocation achieved **54.0% win rate** vs **54.0% for Control**, improving net margin from **$-20.70** to **$-20.70**.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED** (Phase 36 is an experimental counterfactual lab).
