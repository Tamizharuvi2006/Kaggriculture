# EXP-0151: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0151`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `SEMANTIC_TASK_COORDINATOR_SW_QUADRANT`  
> **Variable Family**: `Semantic_Task_Coordination` (Dependency-Protected Task Allocation)  
> **Evidence Source**: reports/SPATIAL_POLICY_3_REPORT.md

---

## 1. Formal Mechanism Hypothesis

> *"By implementing a Semantic Task Coordinator that explicitly protects high-criticality infrastructure milestones (e.g. Worker #2 & #3 Step 159 BUILD_PASTURE and Worker #0 Step 170 PICKUP COW in the CRITICAL_TASK_REGISTRY), APEX dynamically allocates unreserved worker capacity during Steps 153–170 to till and plant 4 strawberry seeds on the newly unlocked SW quadrant. This achieves early crop scaling (+ $1,450.00 MCV) with 100% pasture construction and 100% animal deployment, eliminating both the coordinate drift of EXP-0149 and the pasture build failure of EXP-0150."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Target Worker | Critical Milestones Protected | Land 2 Trigger | SW Target Quadrant | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-151-01`** | None (Control) | All (Baseline) | Step 170 | N/A | `APEX 3.5 PROD` Control |
| **`CAND-151-02`** | Unreserved PASS | Step 159 Pasture, Step 170 Pickup | Step 152 | SW `(5, 1)..(6, 2)` | Standard Semantic Task Coordinator |
| **`CAND-151-03`** | Unreserved PASS | Step 159 Pasture, Step 170 Pickup | Step 148 | SW `(5, 1)..(6, 2)` | Fast Land Semantic Coordinator |
| **`CAND-151-04`** | Unreserved PASS | Step 159 Pasture, Step 170 Pickup | Step 156 | SW `(5, 1)..(6, 2)` | Conservative Land Semantic Coordinator |
| **`CAND-151-05`** | Worker #4 Only | Step 159 Pasture, Step 170 Pickup | Step 152 | SW `(5, 1)..(6, 2)` | Dedicated Worker #4 Semantic Allocator |
| **`CAND-151-06`** | Worker #5 Only | Step 159 Pasture, Step 170 Pickup | Step 152 | SW `(5, 1)..(6, 2)` | Dedicated Worker #5 Semantic Allocator |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00 AND Critical_Task_Violations == 0.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
