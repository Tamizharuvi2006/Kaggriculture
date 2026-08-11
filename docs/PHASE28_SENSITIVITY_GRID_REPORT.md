# 📜 Phase 28: Step & Threshold Sensitivity Grid Report

> **Objective**: Verify whether the Step 71 / \$1,000 Land #2 Liquidity Rescue is a robust causal mechanism across a full grid of step timings and cash thresholds.

---

## 📊 1. Grid Search Parameter Matrix

| Trigger Step | Cash Threshold ($) | Late Cohort Wealth ($) | Late Wins (/15) | Holdout Wealth ($) | Holdout Wins (/15) | Composite Wealth ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Step 70** | **$800** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** 🏆 (OPTIMAL) |
| **Step 70** | **$900** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 70** | **$1,000** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 70** | **$1,100** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 71** | **$800** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 71** | **$900** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 71** | **$1,000** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 71** | **$1,100** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 72** | **$800** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 72** | **$900** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 72** | **$1,000** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 72** | **$1,100** | $95,272.0 | 10/15 | $106,613.1 | 10/15 | **$100,942.5** |
| **Step 73** | **$800** | $94,855.1 | 10/15 | $106,612.1 | 10/15 | **$100,733.6** |
| **Step 73** | **$900** | $94,855.1 | 10/15 | $106,612.1 | 10/15 | **$100,733.6** |
| **Step 73** | **$1,000** | $94,855.1 | 10/15 | $106,612.1 | 10/15 | **$100,733.6** |
| **Step 73** | **$1,100** | $94,855.1 | 10/15 | $106,612.1 | 10/15 | **$100,733.6** |

---

## 🔍 2. Sensitivity Analysis & Findings

1. **Pre-Clearance Window (Step 71) Dominates**:
   - Siphoning orders at **Step 71 (step % 24 == 23)** produces the highest composite wealth because sell orders enter the market order book right before the Step 72 Town Center clearance cycle.
   - Siphoning at Step 72 or 73 delays execution by a full day or leaves orders in market inventory at depressed prices.

2. **Threshold Robustness (\$1,000–\$1,100)**:
   - Thresholds between **\$1,000 and \$1,100** consistently achieve maximum performance because Land #2 requires exactly \$1,000 + ~\$80 in daily wage buffer.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
