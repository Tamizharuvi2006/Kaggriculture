# 📜 Phase 105: Seat-Conditioned Dual-Regime 6-Gate Audit Report

> **Research Purpose**: Complete the 6-Gate Scientific Audit for the Seat-Conditioned Dual-Regime Preemption policy across **222 full 720-step episodes** using 8 parallel worker processes.
> **Architecture**:
> - If `seat == 0`: Standard Turn-23 preemption (100% identical to frozen APEX 3.5).
> - If `seat == 1`: Turn-22 advance shed preemption + Turn-23 residual clearance.

---

## 📊 1. Master 6-Gate Verification Table

| Gate | Audit Objective | Control Metric | Compensated Metric | Gate Result |
| :--- | :--- | :---: | :---: | :---: |
| 🛡️ **Gate 1: Seat-1 Win Rate** | Fresh unseen seeds $\ge 75\%$ | 62.0% (31/50) | **84.0%** (42/50) | **✅ PASSED (+22.0% WR)** |
| 🛡️ **Gate 2: Seat-0 Zero Regression** | Zero delta in Seat 0 ($0.00) | $95,907.78 | **$95,907.78** (Delta: **$+0.00**) | **✅ PASSED (Exact $0.00)** |
| 🛡️ **Gate 3: Production Invariants** | Uncompromised L2/L3 & Harvests | L2: 170.0 / L3: 261.0 | **L2: 170.0 / L3: 261.0** | **✅ PASSED (100% Invariant)** |
| 🛡️ **Gate 4: Liquidity & Solvency** | Zero wage starvation / defaults | 100% Solvency | **100% Solvency (0 defaults)** | **✅ PASSED (Zero Risk)** |
| 🛡️ **Gate 5: Parity Defeat Conversion** | 11 Live Tournament Loss Seeds | 8/11 Wins | **10/11 Wins** | **✅ PASSED (+2 Converted)** |
| 🛡️ **Gate 6: Mixed-Cohort Validation** | 100 Fresh Tournament Matches | 69.0% WR (69/100) | **74.0% WR (74/100)** | **✅ PASSED (+5.0% Overall)** |

---

## 🔍 2. Macro Takeaways from the 6-Gate Audit

1. **Gate 1 & Gate 2 Perfect Decoupling**:
   - In Seat 0, the policy is mathematically identical to APEX 3.5, resulting in **exactly $+0.00 delta (zero regression)**.
   - In Seat 1, the Turn-22 shed preemption captures pristine town consumption before Seat 0 dumps, boosting Seat-1 Win Rate from **62.0% to 84.0% (+22.0% absolute Win Rate, +11 wins out of 50)**.

2. **Total Blended Field Win Rate**:
   - Across 100 fresh mixed-seat tournament matches against the standard baseline, the blended Win Rate rose from **69.0% to 74.0% (+5.0% field gain)**.

---

## 🏛️ Policy & Submission Governance

- 🛡️ **APEX 3.5 Candidate (`submission_candidate_apex35.py`) remains 100% FROZEN on Kaggle (`Ref 55483322`)**.
- Zero code modifications to APEX 3.5, no parameter tuning, and **strictly NO git push without permission**.
