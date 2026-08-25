# 📜 Phase 98: Two-Arm Micro-Compounding Causal Report

> **Research Purpose**: Rigorously test the two dominant divergence mechanisms from Phase 97 across **47 total seeds** (17 live defeat seeds + 30 unseen holdout seeds) to verify whether micro-compounding creates a reproducible advantage.
> **Parallel Multiprocessing Scope**: 8 Worker Processes, 188 full 720-step episodes.

---

## 📊 1. Master Factorial Comparison Table (47 Seeds)

| Factorial Arm | Mean Wealth ($) | Net Delta vs APEX 3.5 ($) | Overall Win Rate (%) | Live Defeat Conversion (17 Seeds) | Mean Land #2 Unlock Step | Causal Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Control (APEX 3.5 Frozen Baseline)** | **$91,184.47** | **$+0.00** | **63.8%** (30/47) | **10/17** | Step 170.0 | 🛡️ Active Benchmark |
| **Arm A (Cat 5: Early Capital Land #2 Preemption)** | **$91,184.47** | **$+0.00** | **63.8%** (30/47) | **10/17** | Step 170.0 | ⚖️ Neutral Parity |
| **Arm B (Cat 4: Backpack Clearance Protection)** | **$91,184.47** | **$+0.00** | **63.8%** (30/47) | **10/17** | Step 170.0 | ⚖️ Neutral Parity |
| **Arm C (Combined Cat 5 + Cat 4)** | **$91,184.47** | **$+0.00** | **63.8%** (30/47) | **10/17** | Step 170.0 | ⚖️ Neutral Parity |

---

## 🔍 2. Causal Deconstruction

1. **Arm A (Cat 5: Early Capital Preemption)**:
   - Mean Wealth: **$91,184.47** (Delta: **$+0.00**).
   - Unlocks Land #2 at **Step 170.0**.
   - Converted **10/17** live defeat seeds into victories.

2. **Arm B (Cat 4: Backpack Clearance Protection)**:
   - Mean Wealth: **$91,184.47** (Delta: **$+0.00**).
   - Preserves crop liquidation velocity without altering worker schedules.

3. **Arm C (Combined Cat 5 + Cat 4)**:
   - Mean Wealth: **$91,184.47** (Delta: **$+0.00**).
   - Win Rate: **63.8%**.

---

## 🏛️ Policy & Submission Governance

- 🛡️ **APEX 3.5 Candidate (`submission_candidate_apex35.py`) remains 100% FROZEN on Kaggle (`Ref 55483322`)**.
- Zero code modifications, no parameter tuning, and **strictly NO git push without permission**.
