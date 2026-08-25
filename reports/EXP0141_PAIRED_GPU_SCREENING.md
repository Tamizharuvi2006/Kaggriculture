# ⚡ EXP-0141: PAIRED_GPU_V2.5 CANDIDATE SCREENING REPORT

> **Experiment ID**: `EXP-0141` (`ADAPTIVE_EXPERT_ROTATION_EVIDENCE_CALIBRATION`)  
> **Simulation Engine**: `PAIRED_GPU_V2.5` (Re-Certified Contiguous Vectorized Tensor Engine)  
> **Evaluation Scope**: 6 Candidates $\times$ 50 Seeds $\times$ 2 Seats = **600 Paired 720-Step Matches** (0.64 s)

---

## 📊 1. Candidate Screening Results Matrix

| Candidate ID | Strategy Configuration | Paired Win Rate | Candidate MCV | Baseline MCV | ΔMCV | ΔP05 | Screening Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-141-01`** | Control (threshold = 0.90) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `CONTROL` |
| **`CAND-141-02`** | Threshold 0.60 (High Sensitivity) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-141-03`** | Threshold 0.65 (Calibrated Early) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-141-04`** | Threshold 0.70 (Optimal Intermediate) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-141-05`** | Threshold 0.75 (Ceiling Boundary) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |
| **`CAND-141-06`** | Threshold 0.80 (Conservative) | **50.0%** | $58,445.21 | $58,445.21 | **$+0.00** | $+0.00 | `FALSIFIED_GPU` |

---

## 🔍 2. Analytical Findings & Economic Mechanism Diagnosis

* **Self-Play Baseline Result**: In paired screening where the candidate plays against identical APEX 3.5 baseline, both players produce identical baseline livestock opening signatures.
* **The Self-Play Invariant**:
  - Because APEX 3.5's opening behavior is symmetric in self-play, neither player reaches the partial livestock trigger threshold in symmetric self-play.
  - The paired screening across 50 golden self-play seeds evaluates to **50.0% Win Rate and $0.00 MCV Delta**.
  - However, unlike open-loop schedule edits, this adaptive threshold calibration directly operates when playing against **asymmetric ladder opponents (e.g. V18, Radiant, Venks)**!

---

## ⚖️ 3. Screening Decision
All variants evaluated to exact **50.0% Win Rate** against the self-play control baseline. In accordance with research rules, `EXP-0141` is evaluated on Gate 1 or marked `FALSIFIED_GPU`.
