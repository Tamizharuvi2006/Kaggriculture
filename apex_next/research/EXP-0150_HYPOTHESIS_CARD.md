# EXP-0150: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0150`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `CLOSED_LOOP_DETOUR_AND_PATH_RECONCILIATION`  
> **Variable Family**: `Spatial_Worker_Routing / Path_Reconciliation`  
> **Evidence Source**: reports/SPATIAL_POLICY_2_FORENSIC.json

---

## 1. Formal Mechanism Hypothesis

> *"By executing a temporary productive detour into the newly unlocked SW quadrant during Steps 153–164 (tilling and planting 4 strawberry tiles), and strictly enforcing a return-to-anchor routing protocol during Steps 165–170, APEX achieves 100% path reconciliation at Step 171 (0.00 coordinate error). This preserves all +$1,120.00 MCV gains from early strawberry cultivation while completely eliminating the coordinate de-synchronization and path corruption discovered in EXP-0149."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Detour Worker | Detour Window | Return Window | Anchor Position | Expected Post-Reconciliation Error | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`CAND-150-01`** | None (Control) | N/A | N/A | N/A | `0.00` | `APEX 3.5 PROD` Control |
| **`CAND-150-02`** | Worker #2 | Steps 153–164 | Steps 165–170 | `(3, 4)` | `0.00` | Standard Reconciled Detour Policy |
| **`CAND-150-03`** | Worker #2 | Steps 153–162 | Steps 163–170 | `(3, 4)` | `0.00` | Conservative Return Buffer (8 steps return) |
| **`CAND-150-04`** | Worker #3 | Steps 156–165 | Steps 166–170 | `(4, 4)` | `0.00` | Worker #3 Reconciled Detour |
| **`CAND-150-05`** | Worker #2 + #3 | Steps 153–164 | Steps 165–170 | `(3, 4), (4, 4)` | `0.00` | Dual Worker Reconciled Detour |
| **`CAND-150-06`** | Worker #2 | Steps 153–164 | Steps 165–170 | `(3, 4)` | `0.00` | Reconciled Detour with 6 Strawberry Seeds |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00 AND Post_Reconciliation_Error == 0.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
