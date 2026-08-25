# EXP-0152: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0152`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `MACRO_SEMANTIC_TASK_COORDINATOR`  
> **Variable Family**: `Macro_Semantic_Task_Coordination` (Full-Game Closed-Loop Task Graph)  
> **Evidence Source**: reports/SPATIAL_POLICY_4_MACRO_REPORT.md

---

## 1. Formal Mechanism Hypothesis

> *"By implementing a Full-Game Macro Semantic Task Coordinator that operates across all 720 steps, APEX dynamically prioritizes high-value physical execution (early SW quadrant cultivation, Hour 22 pre-clearance backpack drops, and terminal feed conservation) while strictly protecting all 242 critical milestones (pasture construction, animal pickups, daily feedings) in the CRITICAL_TASK_REGISTRY. This lifts match earnings by +$3,940.00 MCV, converting 76.1% of historical ladder losses into wins across diverse tournament opponents with 100% solvency and zero coordinate drift."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Macro Policy Scope | Critical Task Invariant | Fallback Policy | Expected Recovery Rate | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-152-01`** | None (Control) | All (Baseline) | `APEX 3.5 PROD` | `0.0%` | Baseline Control (Fixed Schedule) |
| **`CAND-152-02`** | Full 3-Phase (A+B+C) | 242 Milestones Protected | `_FIXED_SCHEDULE_B85` | `76.1%` | Unified Macro Semantic Coordinator |
| **`CAND-152-03`** | Phase A + B Only | 242 Milestones Protected | `_FIXED_SCHEDULE_B85` | `65.2%` | Early Cultivation + Backpack Drop Coordinator |
| **`CAND-152-04`** | Phase A Only | 242 Milestones Protected | `_FIXED_SCHEDULE_B85` | `47.8%` | Early Cultivation Coordinator |
| **`CAND-152-05`** | Phase B Only | 242 Milestones Protected | `_FIXED_SCHEDULE_B85` | `28.3%` | Backpack Drop Coordinator |
| **`CAND-152-06`** | Conservative Full 3-Phase | 242 Milestones Protected | `_FIXED_SCHEDULE_B85` | `71.7%` | Distance-Constrained Macro Coordinator |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00 AND Critical_Task_Violations == 0.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
