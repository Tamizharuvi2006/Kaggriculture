# EXP-0149: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0149`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `DYNAMIC_WORKER_ROUTING_OVERLAY`  
> **Variable Family**: `Spatial_Worker_Routing` (Closed-Loop Spatial Coordination)  
> **Evidence Source**: reports/SPATIAL_POLICY_FORENSIC.json

---

## 1. Formal Mechanism Hypothesis

> *"By intercepting idle and PASS worker actions inside `_apply_fixed_board_adaptation()` when the SW quadrant is unlocked (Steps 152–170), APEX dynamically reroutes available workers to till and plant 6 strawberry seeds on the newly unlocked quadrant 15 steps earlier than the static schedule. This converts idle worker capacity into 2 additional strawberry harvest cycles (+ $2,240 MCV), breaking the open-loop coordinate bottleneck without altering baseline watering or care tasks."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Routing Strategy | Target Quadrant | Idle Action Scope | Fallback | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-149-01`** | None (Control) | N/A | None | `APEX 3.5 PROD` | Baseline Control (Fixed Coordinate Trace) |
| **`CAND-149-02`** | `DYNAMIC_SW_ROUTING` | SW (Rows 5-9, Cols 0-4) | `PASS` + Idle Transit | Baseline Schedule | Standard Closed-Loop Spatial Overlay |
| **`CAND-149-03`** | `AGGRESSIVE_SW_ROUTING` | SW | `PASS` + Low-Priority Transit | Baseline Schedule | Fast SW Tilling Overlay |
| **`CAND-149-04`** | `CONSERVATIVE_SW_ROUTING`| SW | Strict `PASS` Only | Baseline Schedule | Minimal Safe Spatial Overlay |
| **`CAND-149-05`** | `NO_MELON_SW_ROUTING` | SW | `PASS` Only | Baseline Schedule | Spatial Overlay without Melon Acceleration |
| **`CAND-149-06`** | `PROXIMITY_SW_ROUTING` | SW | Nearest Worker ($\le 3$ tiles)| Baseline Schedule | Distance-Constrained Spatial Overlay |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
