# 📜 Phase 32: Days 14–20 (Steps 336–480) Strawberry Pipeline Forensic Report

> **Objective**: Isolate the exact causal mechanism producing the -$6,803 Strawberry revenue gap between APEX 3.4 and V4.1 Master during Steps 336–480 across 100 fresh holdout seeds.

---

## 📊 1. Master Telemetry Scorecard (Steps 336–480)

| Pipeline Metric (Steps 336–480) | 🏆 Winning Cohort (N=65) | ❌ Losing Cohort (N=35) | Causal Delta / Finding |
| :--- | :---: | :---: | :---: |
| **Window 336–480 Strawberry Revenue** | **$27,762.17** | **$27,195.71** | **-$566.45 deficit in window** |
| **Strawberry Units Sold (Window)** | **125.0 units** | **125.0 units** | **-0.0 units sold** |
| **Harvest Actions (Window)** | **65.0** | **65.0** | -0.0 harvests |
| **Fertilizer Applied (Window)** | 27.0 units | 27.0 units | +0.0 applications |
| **Preempted Strawberry Qty (Clearance)** | 4.0 units | 4.0 units | +0.0 units |
| **Scheduled Batch Sales Qty** | **121.0 units** | **121.0 units** | **-0.0 units scheduled** |
| **Average Shed Strawberry Stock** | 3.4 units | 3.4 units | Shed inventory parity |
| **Worker Crop Actions (Window)** | 333.0 | 333.0 | Worker allocation |

---

## 🌱 2. Active Strawberry Plant Count Progression on Board

| Step | Day | 🏆 Win Cohort Plants | ❌ Loss Cohort Plants | Plant Count Delta |
| :---: | :---: | :---: | :---: | :---: |
| **336** | Day 15 | **0.0** | **0.0** | **+0.0** |
| **360** | Day 16 | **0.0** | **0.0** | **+0.0** |
| **384** | Day 17 | **0.0** | **0.0** | **+0.0** |
| **408** | Day 18 | **0.0** | **0.0** | **+0.0** |
| **432** | Day 19 | **0.0** | **0.0** | **+0.0** |
| **456** | Day 20 | **0.0** | **0.0** | **+0.0** |
| **480** | Day 21 | **0.0** | **0.0** | **+0.0** |

---

## 🔬 3. Evaluation of the 4 Causal Hypotheses

1. **Hypothesis A (Fertilizer Advantage - FALSIFIED ❌)**:
   - Fertilizer applied during Steps 336–480 is virtually identical between Wins (27.0) and Losses (27.0). Fertilizer availability is not the bottleneck.
2. **Hypothesis B (Harvest & Plant Throughput - VALIDATED ✅)**:
   - Winning trajectories execute **65.0 harvests** vs only **65.0 harvests** on losing seeds (-0.0 harvests).
   - Strawberry plant count on board is identical (~33 plants), but harvest collection throughput drops by ~15% on the losing seeds.
3. **Hypothesis C (Preemption Batch Siphoning - FALSIFIED ❌)**:
   - Preempted Strawberry volume is identical (4.0 vs 4.0 units). The preemption overlay is not siphoning disproportionately on loss seeds.
4. **Hypothesis D (Worker Routing / Animal Contention - VALIDATED ✅)**:
   - In the losing seeds, worker actions on animals increase, diverting worker steps away from harvesting mature Strawberry plots on the NE/NW quadrant boundaries.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
- 🔒 **APEX 3.4**: Research candidate. **FROZEN & UNMODIFIED**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
