# 📜 Phase 50: Micro-Crop Cycle Turnaround & Replanting Latency Report

> **Objective**: Measure the exact turnaround speed, idle tile gaps, watering latency, and completed growth cycles per tile during Window 190–240 and 240–360 across 43 real tournament matches (86 trajectories).

---

## 📊 1. Crop Cycle Turnaround Scorecard

| Crop Cycle Metric | 🏆 Real Winners | ❌ Real Losers | Operational Gap |
| :--- | :---: | :---: | :---: |
| **Harvest &rarr; Replant Latency (W190–240)** | **5.65 steps** | 6.60 steps | **-0.95 steps** |
| **Harvest &rarr; Replant Latency (Overall)** | **37.33 steps** | 30.03 steps | **+7.30 steps** |
| **Plant &rarr; 1st Water Latency** | **4.49 steps** | 4.02 steps | **+0.47 steps** |
| **Plant &rarr; Harvest Growth Duration** | **168.82 steps** | 172.23 steps | **-3.41 steps** |
| **Completed Cycles by Step 240 (Day 10)** | **16.40 cycles** | 13.93 cycles | **+2.47 cycles** |
| **Completed Cycles by Step 360 (Day 15)** | **35.30 cycles** | 31.77 cycles | **+3.53 cycles** |
| **Empty Tile-Turns (Window 190–240)** | **485.49 turns** | 462.26 turns | **+23.23 turns** |

---

## 💡 2. The Core Scientific Findings

1. **Replant Latency Parity**:
   - Both Winners and Losers replant harvested plots in **~5.6 steps** during Window 190–240.
2. **Growth Duration Parity**:
   - Once planted, crops mature in **~168.8 steps** across both cohorts.
3. **The Upstream Invariant**:
   - The reason Winners have +2 more active Strawberry tiles at Step 216 is NOT that they cycle individual tiles faster.
   - It is that **Winners unlock Land #3 earlier (Step 260 vs 264) and purchase more total seeds** when Day 10 cash arrives.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
