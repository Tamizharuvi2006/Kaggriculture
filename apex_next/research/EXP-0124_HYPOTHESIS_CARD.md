# EXP-0124: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0124`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `SOLVENCY_GATED_LAND_EXPANSION`  
> **Sole Variable Family**: `Capital_Deployment` (Single-variable isolation)  
> **Evidence Source**: reports/EXP0124_SOLVENCY_FORENSIC_AUDIT.json

---

## 1. Formal Mechanism Hypothesis

> *"Unlocking Land 2 dynamically when liquid cash reaches **>= $1,800 - $2,000** (preserving a strict $800 - $1,000 operating reserve to fully fund 4x strawberry seed purchases, fertilizer, daily worker wages, and animal feed) captures +1 full lifecycle harvest cycle on high-revenue seeds without inducing the capital starvation or downside tail risk observed in EXP-0121."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Min Step | Cash Threshold | Post-Purchase Operating Reserve |
| :--- | :---: | :---: | :---: |
| **`CAND-124-01`** | `170` | `$1,000` | `$0` (APEX 3.5 Control) |
| **`CAND-124-02`** | `120` | `$1,800` | `$800` |
| **`CAND-124-03`** | `120` | `$2,000` | `$1,000` |
| **`CAND-124-04`** | `120` | `$2,200` | `$1,200` |
| **`CAND-124-05`** | `140` | `$1,800` | `$800` |
| **`CAND-124-06`** | `140` | `$2,000` | `$1,000` |

*Total Frozen Grid*: Exactly **6 structured configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2 Screening Funnel**: Screen across 50 fixed seeds (100 paired matches per candidate). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top surviving candidate is submitted to **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
