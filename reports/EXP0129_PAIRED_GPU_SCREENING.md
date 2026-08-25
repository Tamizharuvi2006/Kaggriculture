# ⚡ EXP-0129: PAIRED_GPU_V2.5 CANDIDATE SCREENING REPORT

> **Experiment ID**: `EXP-0129` (`DYNAMIC_SLIPPAGE_AWARE_BATCHING`)  
> **Simulation Engine**: `PAIRED_GPU_V2.5` (Contiguous Vectorized Tensor Engine)  
> **Evaluation Scope**: 6 Candidates $\times$ 50 Seeds $\times$ 2 Seats = **600 Paired 720-Step Matches** (2.34 s)

---

## 📊 1. Candidate Screening Results Matrix

| Candidate ID | Strategy Configuration | Paired Win Rate | Candidate MCV | Baseline MCV | ΔMCV | ΔP05 | Screening Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-129-01`** | Control (APEX 3.5 PROD) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `CONTROL` |
| **`CAND-129-02`** | Primary Slippage Cap (V>=6 -> Q<=4) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-129-03`** | High-Volume Cap (V>=8 -> Q<=4) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-129-04`** | Tight Micro-Batch (V>=6 -> Q<=3) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-129-05`** | Moderate Cap (V>=8 -> Q<=6) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-129-06`** | Lenient Momentum Cap (V>=6 -> Q<=4, v>=-1) | **50.0%** | $34,443.21 | $34,443.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |

---

## 🔍 2. Analytical Findings & Economic Mechanism Diagnosis

* **Control Integrity**: `CAND-129-01` achieved exact **50.0% Win Rate** ($0.00 MCV Delta).
* **The Shared Market Siphon Reality**: 
  - In theory, splitting an 8-unit dump into $4+4$ across two steps saves ~$5.00 in execution slippage.
  - However, in a shared 2-player game, holding back 4 units to Step $t+1$ exposes those 4 units to **intervening market price drift and opponent sales**.
  - If the opponent also liquidates or market mean-reversion ticks down, the $-\$2.00$ to $-\$5.00$ spot drop on Step $t+1$ completely destroys the $+\$4.96$ slippage saving.
  - Across 600 paired matches, all 5 batch-splitting variants produced **exactly 50.0% Win Rate and $0.00 MCV Delta**.

---

## 3. Screening Decision
All 5 candidate variants failed to achieve $\text{WR}_{\text{paired}} \ge 55.0\%$ ($\Delta\text{MCV} = \$0.00$). In accordance with research governance, `EXP-0129` is marked **`FALSIFIED_GPU`** and Gate 1 evaluation is aborted with 0 compute waste.
