# EXP-0130: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0130`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `LATE_GAME_SEED_WASTE_CUTOFF`  
> **Sole Variable Family**: `Capital_Preservation`  
> **Evidence Source**: reports/EXP0130_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"Because strawberries require exactly 48 steps to mature and unharvested immature crops have zero salvage value at Step 720, halting strawberry seed purchases and planting actions at a calibrated cutoff step S_cutoff in [624, 648, 672, 696] eliminates deadweight capital burn, increasing terminal cash balance by up to +$1,320.00 without reducing total realized harvest revenue."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Cutoff Step (S_cutoff) | Cutoff Day/Hour | Strategy Description |
| :--- | :---: | :---: | :--- |
| **`CAND-130-01`** | `None` (Control) | `No Cutoff` | `APEX 3.5 PROD` Control (Continuous planting to end) |
| **`CAND-130-02`** | `Step 672` | `Day 28, Hour 0` | Strict Physical Cutoff (Zero post-672 planting) |
| **`CAND-130-03`** | `Step 648` | `Day 27, Hour 0` | Conservative Cutoff (24h safety buffer before final harvest) |
| **`CAND-130-04`** | `Step 624` | `Day 26, Hour 0` | Early Cutoff (48h safety buffer) |
| **`CAND-130-05`** | `Step 696` | `Day 29, Hour 0` | Late Cutoff (Only halts final 24h plantings) |

*Total Frozen Grid*: Exactly **5 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (500 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
