# EXP-0136: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0136`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `DAY_1_COW_DOMINANCE_VS_SHEEP_ROI_REALLOCATION`  
> **Sole Variable Family**: `Asset_Allocation`  
> **Evidence Source**: reports/EXP0136_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"Because cows generate 16.9x higher net lifetime profit per dollar invested than sheep ($16,900 net profit per cow vs $2,400 per sheep over 120 milking cycles), reallocating Day 1 opening capital from 1 Sheep ($1,200) into additional Cows ($500 each) increases continuous 6-hour milk cashflow by up to +$33,800 without exceeding Pasture 1 capacity (5/5) or overloading worker feeding labor."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Day 1 Cows | Day 1 Sheep | Initial Spend | Day 1 Cash Saved | Strategy Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-136-01`** | `3 Cows` | `1 Sheep` | `$2,700` | `$0.00` (Control) | `APEX 3.5 PROD` Control (3 Cows + 1 Sheep) |
| **`CAND-136-02`** | `5 Cows` | `0 Sheep` | `$2,500` | `+$200.00` | Full Cow Dominance (5 Cows, Pasture 1 Full) |
| **`CAND-136-03`** | `4 Cows` | `0 Sheep` | `$2,000` | `+$700.00` | Conservative Cow Allocation (4 Cows + $700 Cash) |
| **`CAND-136-04`** | `4 Cows` | `1 Sheep` | `$3,200` | `-$500.00` | Maximum Animal Expansion (4 Cows + 1 Sheep) |
| **`CAND-136-05`** | `3 Cows` | `0 Sheep` | `$1,500` | `+$1,200.00` | Pure Cash Preservation (3 Cows + $1,200 Cash) |
| **`CAND-136-06`** | `2 Cows` | `2 Sheep` | `$3,400` | `-$700.00` | Sheep-Heavy Portfolio (2 Cows + 2 Sheep) |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
