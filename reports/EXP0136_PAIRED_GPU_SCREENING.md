# ⚡ EXP-0136: PAIRED_GPU_V2.5 CANDIDATE SCREENING REPORT

> **Experiment ID**: `EXP-0136` (`DAY_1_COW_DOMINANCE_VS_SHEEP_ROI_REALLOCATION`)  
> **Simulation Engine**: `PAIRED_GPU_V2.5` (Optimized Contiguous Vectorized Tensor Engine)  
> **Evaluation Scope**: 6 Candidates $\times$ 50 Seeds $\times$ 2 Seats = **600 Paired 720-Step Matches** (0.71 s)

---

## 📊 1. Candidate Screening Results Matrix

| Candidate ID | Strategy Configuration | Paired Win Rate | Candidate MCV | Baseline MCV | ΔMCV | ΔP05 | Screening Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-136-01`** | Control (3 Cows + 1 Sheep) | **50.0%** | $50,712.13 | $50,712.13 | **$+0.00** | $+0.00 | `CONTROL` |
| **`CAND-136-02`** | Full Cow Dominance (5 Cows + 0 Sheep) | **100.0%** | $83,400.11 | $50,480.06 | **$+32,920.04** | $+31,889.00 | `CLEARED_GPU` |
| **`CAND-136-03`** | Conservative Cow Pivot (4 Cows + 0 Sheep) | **100.0%** | $67,692.02 | $50,594.02 | **$+17,098.00** | $+16,581.27 | `CLEARED_GPU` |
| **`CAND-136-04`** | Maximum Animal Expansion (4 Cows + 1 Sheep) | **100.0%** | $66,492.02 | $50,594.02 | **$+15,898.00** | $+15,381.27 | `CLEARED_GPU` |
| **`CAND-136-05`** | Pure Cash Preservation (3 Cows + 0 Sheep) | **100.0%** | $51,912.13 | $50,712.13 | **$+1,200.00** | $+1,200.00 | `CLEARED_GPU` |
| **`CAND-136-06`** | Sheep-Heavy Portfolio (2 Cows + 2 Sheep) | **0.0%** | $33,656.86 | $50,835.30 | **$-17,178.43** | $-16,659.18 | `FALSIFIED_GPU` |

---

## 🔍 2. Analytical Findings & Economic Mechanism Diagnosis

* **Control Baseline**: `CAND-136-01` achieved exact **50.0% Win Rate** ($0.00 MCV Delta).
* **Massive Win-Condition Victory**: **`CAND-136-02` (5 Cows + 0 Sheep)** achieved **`100.0%` Paired Win Rate** with **`+$32,920.04` Mean MCV Lift** and **`+$31,889.00` p05 Tail Lift** across 100 paired matches!
* **The Economic Driver**:
  - Reallocating Day 1 opening capital from 1 Sheep into 2 Cows unleashes **24 additional milk units every 72 hours** (+120 milk units across the 30-day match).
  - Even after accounting for shared market volume slippage and wheat feeding costs, the candidate generates a permanent, compounding cashflow separation over the baseline.

---

## 🏆 3. Screening Decision: `CLEARED_GPU` (Promoting CAND-136-02 to Gate 1)
`CAND-136-02` cleared the pre-registered screening requirement ($	ext{WR}_{	ext{paired}} = 100.0% \ge 55.0\%$, $\Delta\mu_{	ext{MCV}} = +$32,920.04 > 0$). It is officially promoted to **Gate 1 Exact Replay on `kaggle_environments v1.32.6`**.
