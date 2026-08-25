# ⚡ EXP-0137: PAIRED_GPU_V2.5 CANDIDATE SCREENING REPORT

> **Experiment ID**: `EXP-0137` (`MID_GAME_SECOND_WAVE_COW_ACCELERATION`)  
> **Simulation Engine**: `PAIRED_GPU_V2.5` (Re-Certified Contiguous Vectorized Tensor Engine)  
> **Evaluation Scope**: 6 Candidates $\times$ 50 Seeds $\times$ 2 Seats = **600 Paired 720-Step Matches** (0.63 s)

---

## 📊 1. Candidate Screening Results Matrix

| Candidate ID | Strategy Configuration | Paired Win Rate | Candidate MCV | Baseline MCV | ΔMCV | ΔP05 | Screening Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-137-01`** | Control (Wave 2 @ Step 156) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `CONTROL` |
| **`CAND-137-02`** | Immediate Reinvestment (Wave 2 @ Step 96) | **100.0%** | $61,148.35 | $58,431.28 | **$+2,717.07** | $+2,683.61 | `CLEARED_GPU` |
| **`CAND-137-03`** | Intermediate Acceleration (Wave 2 @ Step 120) | **100.0%** | $60,064.95 | $58,436.87 | **$+1,628.10** | $+1,586.92 | `CLEARED_GPU` |
| **`CAND-137-04`** | Conservative Acceleration (Wave 2 @ Step 144) | **100.0%** | $58,985.39 | $58,442.43 | **$+542.97** | $+522.01 | `CLEARED_GPU` |
| **`CAND-137-05`** | Ultra-Early Acceleration (Wave 2 @ Step 80) | **100.0%** | $61,689.78 | $58,428.50 | **$+3,261.28** | $+3,229.86 | `CLEARED_GPU` |
| **`CAND-137-06`** | Delayed Variant (Wave 2 @ Step 168) | **0.0%** | $57,904.96 | $58,450.34 | **$-545.38** | $-525.31 | `FALSIFIED_GPU` |

---

## 🔍 2. Analytical Findings & Economic Mechanism Diagnosis

* **Control Baseline**: `CAND-137-01` (Step 156) achieved exact **50.0% Win Rate** ($0.00 MCV Delta).
* **Massive Win-Condition Victory**: **`CAND-137-02` (Wave 2 @ Step 96)** achieved **`100.0%` Paired Win Rate** with **`+$2,717.07` Mean MCV Lift** and **`+$2,683.61` p05 Tail Lift** across 100 paired matches!
* **The Economic Driver**:
  - Buying 2 cows at Step 96 instead of Step 156 captures **10 additional milking ticks (+20 milk units)** before mid-game market saturation.
  - Generates continuous, compounding cashflow separation over the baseline throughout all remaining 624 steps.

---

## 🏆 3. Screening Decision: `CLEARED_GPU` (Promoting CAND-137-02 to Gate 1)
`CAND-137-02` cleared the pre-registered screening requirement ($	ext{WR}_{	ext{paired}} = 100.0% \ge 55.0\%$, $\Delta\mu_{	ext{MCV}} = +$2,717.07 > 0$).
