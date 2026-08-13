# 📜 Phase 66: Mid-Tier Opponent Failure Decomposition Report

> **Objective**: Deconstruct the 77 real APEX 3.3 live matches against the 1100–1300 Elo cohort (31 Wins vs 46 Losses) to identify the empirical root-cause failure modes on the live Kaggle ladder.

---

## 📊 1. Opponent Strength Normalization & Sub-Band Breakdown

| Opponent Elo Sub-Band | Live Matches | APEX 3.3 Record | Win Rate (%) | APEX 3.3 Wealth ($) | Opponent Wealth ($) | Net Margin ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Band 1 (1100 - 1150 Elo)** | 17 | 10W - 7L - 0D | **58.8%** | $85,787.47 | $88,601.24 | **$-2,813.76** |
| **Band 2 (1150 - 1200 Elo)** | 30 | 11W - 19L - 0D | **36.7%** | $79,693.87 | $78,673.70 | **$+1,020.17** |
| **Band 3 (1200 - 1250 Elo)** | 20 | 9W - 11L - 0D | **45.0%** | $80,755.10 | $82,867.85 | **$-2,112.75** |
| **Band 4 (1250 - 1300 Elo)** | 10 | 1W - 9L - 0D | **10.0%** | $88,782.40 | $91,046.80 | **$-2,264.40** |

---

## 🔬 2. Wins vs Losses Macro Forensics in Mid-Tier (1100–1300 Elo)

| Match Outcome Cohort | Count | APEX 3.3 Mean Wealth ($) | Opponent Mean Wealth ($) | Mean Margin ($) | Observed Economic State |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **🏆 In Victories** | 31 | **$91,900.87** | $84,299.23 | **+$7,601.65** | Sustained high Strawberry ($150+) & Milk ($120+) realization |
| **❌ In Defeats** | 46 | **$76,156.57** | $83,064.80 | **-$6,908.24** | Clearance preemption dumped into crash troughs ($70–$90/u) |

### Failure Mode Severity Breakdown (46 Defeats):

1. **Narrow Margin Defeats (-$0 to -$3,000)**: **20 / 46 (43.5%)**
   - Mean APEX 3.3 Wealth: **$78,634.05** vs Opponent: **$79,973.50** (Margin: **-$1,339.45**).
   - *Causal Root*: Razor-thin loss caused by missing 1–2 elevated sale windows at end-game.
2. **Moderate Margin Defeats (-$3,000 to -$10,000)**: **15 / 46 (32.6%)**
   - Mean APEX 3.3 Wealth: **$85,710.80** vs Opponent: **$90,357.07** (Margin: **-$4,646.27**).
   - *Causal Root*: Forced clearance sale at `step % 24 == 23` occurring inside a deep downward price spike.
3. **Severe Degradation Defeats (< -$10,000)**: **11 / 46 (23.9%)**
   - Mean APEX 3.3 Wealth: **$58,623.55** vs Opponent: **$78,741.36** (Margin: **-$20,117.82**).
   - *Causal Root*: Mid-game liquidity shock that delayed Land #3 or stalled Strawberry seed replanting cycles.

---

## 🛡️ 3. Formalization of the 3-Gate Submission Protocol

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         3-GATE SCIENTIFIC SUBMISSION PROTOCOL                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Gate 1: Live Failure Reproduction                                                      │
│   - Mechanism must explain a verified live loss pattern on the Kaggle ladder.          │
│   - Status: PASSED (Live APEX 3.3 crash dumping & liquidity starvation verified).      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Gate 2: Counterfactual Causality                                                       │
│   - Replaying failure states with the isolated mechanism recovers farm wealth without  │
│     damaging underlying physical production cadence.                                   │
│   - Status: PASSED (Phase 63 & 65 proved Dual-Regime recovers wealth + 0 starvation).  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Gate 3: Independent Unseen Validation                                                  │
│   - Candidate must survive 100+ fresh unseen seeds with >=65% win rate.                │
│   - Status: PASSED (Phase 64 = 88.0%, Phase 65 = 70.0% across 150 fresh seeds).        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 4. Governance Decision

- 🛡️ **APEX 3.3 (`Ref 55421857`)**: Remains active live probe on Kaggle. **FROZEN**.
- 🚀 **APEX 3.5 (`submission_candidate_apex35.py`)**: Vaulted candidate. **NO UPLOAD / NO TWEAKING**.
- 🏛️ **V4.1 Master (`Ref 55249106`)**: Immutable historical baseline. **RETIRED**.
