# EXP-0141: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0141`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `ADAPTIVE_EXPERT_ROTATION_EVIDENCE_CALIBRATION`  
> **Sole Variable Family**: `Adaptive_Intelligence`  
> **Evidence Source**: reports/EXP0141_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"Because the partial livestock opponent evidence formula in line 4212 is mathematically capped at 0.75 (0.35 + 0.08*(animals - 4)), setting rotation_evidence_threshold = 0.90 permanently suppresses adaptive counter-rotation in 27.6% of tournament matches. Calibrating rotation_evidence_threshold into [0.60, 0.65, 0.70, 0.75, 0.80] unlocks dynamic counter-rotation in 223 suppressed match regimes, improving paired win rate by >= 5.0% without altering open-loop worker movement subroutines."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Rotation Evidence Threshold | Target Regime | Strategy Description |
| :--- | :---: | :---: | :--- |
| **`CAND-141-01`** | `0.90` (Control) | `Baseline APEX 3.5` | `APEX 3.5 PROD` Control (Suppressed Partial Adaptation) |
| **`CAND-141-02`** | `0.60` | `Highly Sensitive` | Activates counter-profile at 4-5 opponent animals |
| **`CAND-141-03`** | `0.65` | `Calibrated Early` | Activates counter-profile at 5-6 opponent animals |
| **`CAND-141-04`** | `0.70` | `Optimal Intermediate` | Activates counter-profile at 6-7 opponent animals |
| **`CAND-141-05`** | `0.75` | `Ceiling Boundary` | Activates counter-profile at full partial evidence (8+ animals) |
| **`CAND-141-06`** | `0.80` | `Conservative` | Activates only on strong multi-signal evidence |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
