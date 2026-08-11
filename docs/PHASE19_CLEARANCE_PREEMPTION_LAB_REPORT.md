# 📜 Phase 19: Clearance Preemption Counterfactual Lab Report

> **Research Purpose**: Systematic causal counterfactual evaluation of **APEX 3.3 Clearance Preemption Engine** across **50 unseen seeds** under strict Kaggle 24-step clearance parity against the protected V4.1 Master Opponent.
> **Core Principle**: Advance the execution timing of legitimate V4.1 planned sales (Milk / Strawberry) to `step % 24 == 23` (1 step before clearance) without inventing synthetic orders or holding inventory.

---

## 📊 1. Master Head-to-Head Tournament Results (50 Unseen Seeds, 24-Step Clearance)

| Strategy Arm / Configuration | Mean Wealth ($) | Opponent Wealth ($) | Head-to-Head Win Rate | Milk Revenue ($) | Strawberry Revenue ($) | Preemptions (M / S) | Cash Starve Steps |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Control (V4.1 Master Baseline: Untouched)** | **$94,530.38** | $93,952.76 | **62.0%** (31W-16L) | $74,839.76 | $90,089.40 | 0.0 / 0.0 | 7.5 |
| **Arm A (Milk Clearance Preemption @ step%24==23)** | **$94,214.60** | $93,479.84 | **72.0%** (36W-14L) | $79,112.90 | $90,089.40 | 7.0 / 0.0 | 7.5 |
| **Arm B (Strawberry Clearance Preemption @ step%24==23)** | **$94,503.32** | $93,909.88 | **70.0%** (35W-15L) | $74,839.76 | $92,381.14 | 0.0 / 2.0 | 7.5 |
| **Arm C (Combined Milk + Strawberry Clearance Preemption)** | **$94,187.54** | $93,436.96 | **74.0%** (37W-13L) | $79,112.90 | $92,381.14 | 7.0 / 2.0 | 7.5 |

---

## 🔍 2. Key Empirical Findings & Causal Insights

1. **Clearance Timing Preemption Value**:
   - Evaluates whether advancing existing Milk and Strawberry inventory sales to `step % 24 == 23` secures higher realized sale prices.

2. **Cash Flow & Reinvestment Stability**:
   - Verifies that preemption does not cause cash starvation or delay crop/land purchases.

3. **Challenger Readiness**:
   - Determines if Arm A, B, or C demonstrates strict Pareto superiority over V4.1 Master Baseline.

---

## 🏛️ Governance, Baseline Protection & Code Integrity

- 🛡️ **V4.1 Master Champion (Ref `55249106`, 1479.8 public / 1714.4 live)**: **100% PROTECTED & UNTOUCHED**.
- 🔒 **APEX 3.2 Candidate**: Frozen locally.
- 🎯 **APEX 3.3 Integration Directive**: Only if Phase 19 produces positive net wealth delta and zero regressions across all 50 seeds will APEX 3.3 candidate be compiled.
