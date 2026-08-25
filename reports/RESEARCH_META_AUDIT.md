# TASK B: RESEARCH META-AUDIT (EXP-0113 THROUGH EXP-0120)

> **Objective**: Quantify why 8 consecutive GPU-discovered candidates achieved strong local screening metrics but converted to exactly **50.0% Win Rate / +$0 MCV** under official Gate 1 exact replay.

---

## Summary of 8 Consecutive Research Cycles

| Experiment | Target Hypothesis | GPU Win Rate | GPU Delta MCV | Gate 1 Win Rate | Gate 1 Delta MCV | Official Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`EXP-0113`** | Collapse Exit Timing | 64.0% | +$18,400 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0114`** | MA Sell Suppression | 58.0% | +$12,200 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0115`** | Seed Buy Deferral | 62.0% | +$8,500 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0116`** | Milk/Wool Hold | 60.0% | +$5,200 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0117`** | $500 Safe Buffer | 61.9% | +$7,300 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0118`** | Late Milk Timing (T2) | 100.0% | +$52 | **50.0%** | **-$2** | `FALSIFIED` |
| **`EXP-0119`** | Plant Priority (p4) | 100.0% | +$218 | **50.0%** | **+$0** | `FALSIFIED` |
| **`EXP-0120`** | Tri-Crop Portfolio | 100.0% | +$100 | **50.0%** | **+$0** | `FALSIFIED` |

---

## Core Diagnosis: Why Solo Screening Fails to Predict Gate 1

### 1. The Solo-Engine Blindness Problem
The GPU screening engine evaluates candidates in **isolated solo mode** where market prices evolve exogenously. In the official Kaggle environment, **both players interact in a shared market order book**:
* When Candidate sells milk/strawberries, it depresses the price for both players.
* Internal micro-optimizations produce small cash timing shifts in solo mode, but in a shared 2-player match, the baseline opponent absorbs the market or counter-acts within the same turn window, resulting in **exact mathematical parity (50.0% WR)**.

### 2. Paired Seat-Swapping Parity Wall
Solo GPU screening only simulates Seat 0. Official Gate 1 runs **92 paired matches** (Seat 0 vs Seat 1 and Seat 1 vs Seat 0). Any asymmetric first-mover edge in solo play is completely cancelled out by the paired seat mirror.

---

## Concrete Engine Redesign Proposal: `PAIRED_OPPONENT_GPU_SIMULATOR (V2)`

1. **Paired Co-Simulation**: Run Candidate and Baseline simultaneously in the **same in-memory game instance**.
2. **Shared Market Dynamics**: Route both agents' market orders through the same bid/ask price impact functions.
3. **Paired Seat Balancing**: Always execute each screening seed twice with swapped player indices.
4. **Aligned Multi-Objective Score**:
   ScreenScore = 0.50 * WinRate_paired + 0.30 * (Delta_MCV / 1000) + 0.20 * (Delta_p05 / 1000) - 2.0 * Delta_PASS
