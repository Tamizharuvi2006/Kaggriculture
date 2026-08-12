# 📜 Phase 58: Land #3 Unlock Velocity x NW Harvest Clearance Factorial Report

> **Objective**: Evaluate whether accelerated Land #3 unlocking (Step 240 vs Step 260) and/or prioritized NW harvest clearance causally expands the mid-game Strawberry pipeline across 50 fresh unseen seeds.

---

## 📊 1. 2x2 Factorial Scorecard (50 Fresh Seeds)

| Factorial Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Land #3 Step (T_l3) | SW Plant Step (T_sw) | Unlock->Plant Latency | Straw @ 360 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arm A Control** | Current APEX 3.4 Control | **27/50 (54.0%)** | $94,465.38 | **$-17.66** | Step 261.0 | Step 178.0 | **-83.0 steps** | **39.1 tiles** |
| **Arm B Land3 Timing** | Land #3 at Step 240+ if Cash >= $2k | **27/50 (54.0%)** | $94,465.38 | **$-17.66** | Step 259.9 | Step 178.0 | **-81.9 steps** | **39.1 tiles** |
| **Arm C Nw Clearance** | Prioritized NW Harvest Clearance | **0/50 (0.0%)** | $46,862.84 | **$-89,163.10** | Step nan | Step 178.0 | **nan steps** | **4.7 tiles** |
| **Arm D Combined** | Early Land #3 + NW Clearance | **0/50 (0.0%)** | $53,700.00 | **$-81,876.28** | Step 297.7 | Step 178.0 | **-119.7 steps** | **9.4 tiles** |

---

## 💡 2. Causal Attribution & Interaction Analysis

1. **Main Effect of Land #3 Unlock Velocity (Arm B vs Control)**:
   - Land #3 Step: **Step 259.9 vs Step 261.0** (1.1 steps faster).
   - Net Delta: **$-17.66**, Win Rate: **54.0%**, Straw @ 360: **39.1 vs 39.1 tiles**.
2. **Main Effect of NW Harvest Clearance (Arm C vs Control)**:
   - Net Delta: **$-89,163.10**, Win Rate: **0.0%**, Straw @ 360: **4.7 vs 39.1 tiles**.
3. **Combined Interaction Effect (Arm D vs Control)**:
   - Net Delta: **$-81,876.28**, Win Rate: **0.0%**, Straw @ 360: **9.4 vs 39.1 tiles**.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
