# EXP-0131: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0131`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `TERMINAL_WHEAT_FEED_EXACT_CALIBRATION`  
> **Sole Variable Family**: `Capital_Preservation`  
> **Evidence Source**: reports/EXP0131_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"By clamping terminal wheat purchases in Steps 650-718 to exact remaining cow feeding demand D_rem = max(0, N_cows * ((720 - t) // 6) - wheat_shed + buffer), APEX eliminates 33 units of unconsumed excess wheat in shed at Step 720, preserving +$180 to +$450 in net cash without dropping a single cow milk production cycle."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Demand Buffer (Units) | Trigger Step | Strategy Description |
| :--- | :---: | :---: | :--- |
| **`CAND-131-01`** | `None` (Control) | `N/A` | `APEX 3.5 PROD` Control (Uncapped static schedule) |
| **`CAND-131-02`** | `+0 Units` | `Step 650` | Exact Remaining Demand (Zero excess wheat) |
| **`CAND-131-03`** | `+2 Units` | `Step 650` | Exact Demand + 2 Units Buffer |
| **`CAND-131-04`** | `+4 Units` | `Step 650` | Exact Demand + 4 Units Buffer |
| **`CAND-131-05`** | `+6 Units` | `Step 650` | Exact Demand + 6 Units Buffer |
| **`CAND-131-06`** | `+0 Units` | `Step 672` | Strict Final-48h Cutoff (Zero buffer from Day 28) |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
