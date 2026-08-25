# EXP-0137: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0137`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `MID_GAME_SECOND_WAVE_COW_ACCELERATION`  
> **Sole Variable Family**: `Capital_Pacing`  
> **Evidence Source**: reports/EXP0137_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"Because Day 3 crop harvests generate >$3,200 in liquid capital and Pasture 1 has 2 free capacity slots (3/5 full), accelerating the Wave 2 purchase of 2 Cows from Step 156 (Day 6.5) to Step S_wave2 in [96, 120, 144] captures up to 10 additional physical milking cycles (+20 milk units), generating +$2,900.00 net cashflow without endangering the Step 170 Land 2 purchase."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Wave 2 Step (S_wave2) | Timing Phase | Physical Worker Transport | Strategy Description |
| :--- | :---: | :---: | :---: | :--- |
| **`CAND-137-01`** | `Step 156` (Control) | `Day 6.5` | Baseline Sequence | `APEX 3.5 PROD` Control (Delayed Wave 2) |
| **`CAND-137-02`** | `Step 96` | `Day 4.0` | S97 Pickup / S100 Place | Immediate Post-Harvest Reinvestment |
| **`CAND-137-03`** | `Step 120` | `Day 5.0` | S121 Pickup / S124 Place | Intermediate Wave 2 Acceleration |
| **`CAND-137-04`** | `Step 144` | `Day 6.0` | S145 Pickup / S148 Place | Conservative Wave 2 Acceleration (12h early) |
| **`CAND-137-05`** | `Step 80` | `Day 3.3` | S81 Pickup / S84 Place | Ultra-Early Wave 2 Acceleration |
| **`CAND-137-06`** | `Step 168` | `Day 7.0` | S169 Pickup / S172 Place | Delayed Control Variant (12h late) |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
