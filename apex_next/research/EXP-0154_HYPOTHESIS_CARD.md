# EXP-0154: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0154`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `CLOSED_LOOP_WORKER_3_POST_PASTURE_SW_ALLOCATION`  
> **Variable Family**: `Spatial_Worker_Routing / Semantic_Eligibility`  
> **Evidence Source**: reports/EXP0154_WORKER_ELIGIBILITY.json

---

## 1. Formal Mechanism Hypothesis

> *"By strictly protecting Worker #2 & Worker #3 at Step 159 to execute BUILD_PASTURE with 100% capacity, and dynamically allocating Worker #3 during its verified 8-step post-pasture idle window (Steps 160–167) to till and plant strawberry seeds on the SW quadrant before returning to anchor tile (3, 4) at Step 170, APEX achieves early SW quadrant production (+ $1,450.00 MCV) with zero pasture build displacement and zero coordinate drift."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Worker Target | Pasture Step 159 Invariant | SW Detour Window | Anchor Return Step | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-154-01`** | None (Control) | Both Workers (Baseline) | N/A | N/A | `APEX 3.5 PROD` Control |
| **`CAND-154-02`** | Worker #3 | 100% Protected (Step 159) | Steps 160–167 | Step 170 | Standard Post-Pasture SW Allocation |
| **`CAND-154-03`** | Worker #3 | 100% Protected (Step 159) | Steps 160–166 | Step 169 | Fast Return Buffer |
| **`CAND-154-04`** | Worker #3 | 100% Protected (Step 159) | Steps 160–168 | Step 170 | Extended Tilling Window |
| **`CAND-154-05`** | Worker #3 | 100% Protected (Step 159) | Steps 160–167 | Step 170 | Post-Pasture Detour (4 Seeds) |
| **`CAND-154-06`** | Worker #3 | 100% Protected (Step 159) | Steps 160–167 | Step 170 | Post-Pasture Detour (6 Seeds) |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00 AND Pasture_2_Built == True.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
