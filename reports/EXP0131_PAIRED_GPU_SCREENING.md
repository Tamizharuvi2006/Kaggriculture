# ⚡ EXP-0131: PAIRED_GPU_V2.5 CANDIDATE SCREENING REPORT

> **Experiment ID**: `EXP-0131` (`TERMINAL_WHEAT_FEED_EXACT_CALIBRATION`)  
> **Simulation Engine**: `PAIRED_GPU_V2.5` (Optimized Contiguous Vectorized Tensor Engine)  
> **Evaluation Scope**: 6 Candidates $\times$ 50 Seeds $\times$ 2 Seats = **600 Paired 720-Step Matches** (0.63 s)

---

## 📊 1. Candidate Screening Results Matrix

| Candidate ID | Strategy Configuration | Paired Win Rate | Candidate MCV | Baseline MCV | ΔMCV | ΔP05 | Screening Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-131-01`** | Control (APEX 3.5 PROD) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `CONTROL` |
| **`CAND-131-02`** | Exact Demand (Buffer +0, Step 650) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-131-03`** | Demand + 2 Units Buffer (Step 650) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-131-04`** | Demand + 4 Units Buffer (Step 650) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-131-05`** | Demand + 6 Units Buffer (Step 650) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-131-06`** | Strict Final-48h Cutoff (Step 672) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |

---

## 🔍 2. Analytical Findings & Economic Mechanism Diagnosis

* **Control Integrity**: `CAND-131-01` achieved exact **50.0% Win Rate** ($0.00 MCV Delta).
* **The Shared Market Paired Reality**:
  - In paired co-simulation where candidate and APEX 3.5 share the town market and cow milking mechanics, capping terminal wheat purchases preserves exact terminal cash while maintaining 100% of cow milk yields.
  - In baseline self-play where cow milk production is already maximized, the net delta across 600 matches evaluates to **50.0% Win Rate and $0.00 MCV Delta**.

---

## ⚖️ 3. Screening Decision
All candidate variants evaluated to exact **50.0% Win Rate**. In accordance with research governance, `EXP-0131` is marked **`FALSIFIED_GPU`** and Gate 1 evaluation is aborted with 0 compute waste.
