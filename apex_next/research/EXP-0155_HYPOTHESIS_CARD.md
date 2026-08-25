# EXP-0155: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0155`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `CLOSED_LOOP_RESOURCE_SYNCHRONIZATION`  
> **Variable Family**: `Closed_Loop_Resource_Synchronization` (Seed & Worker Coupling)  
> **Evidence Source**: reports/EXP0155_SEED_LIFECYCLE.json

---

## 1. Formal Mechanism Hypothesis

> *"By purchasing 2 additional strawberry seeds at Step 156 (retaining 2 seeds in the shed after Worker #0's Step 156 plant), Worker #3's dynamic post-pasture detour at Steps 160–167 converts from an empty no-op into 100% successful planting of SW strawberry crops. This completes the full physical chain (Land 2 -> Seeds in Shed -> Pasture 2 Built -> Crop Planted & Watered -> Anchor Return), capturing +$1,450.00 MCV with zero solvency violations and zero coordinate drift."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Seed Purchase Step | Extra Seeds Bought | Worker Target | Pasture Step 159 Invariant | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-155-01`** | N/A (Control) | 0 | None | Protected | `APEX 3.5 PROD` Control |
| **`CAND-155-02`** | Step 156 | 2 Extra Seeds (Qty 3) | Worker #3 | Protected | Standard Synchronized Seed & Worker Policy |
| **`CAND-155-03`** | Step 156 | 1 Extra Seed (Qty 2) | Worker #3 | Protected | Minimal 1-Seed Synchronized Policy |
| **`CAND-155-04`** | Step 156 | 3 Extra Seeds (Qty 4) | Worker #3 | Protected | Aggressive 3-Seed Synchronized Policy |
| **`CAND-155-05`** | Step 152 | 2 Extra Seeds (Qty 3) | Worker #3 | Protected | Early Seed Purchase Policy |
| **`CAND-155-06`** | Step 156 | 2 Extra Seeds (Qty 3) | Worker #3 | Protected | Fast Return Buffer Policy |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00 AND Successful_PLANT_Rate == 100%.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
