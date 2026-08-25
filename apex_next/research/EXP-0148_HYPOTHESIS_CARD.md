# EXP-0148: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0148`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `DYNAMIC_DAY4_MELON_LIQUIDITY_LAND_ACCELERATION`  
> **Variable Family**: `Composite_Adaptive_Policy` (Strictly Documented Causal Coupling)  
> **Evidence Source**: reports/EXP0148_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"By executing immediate melon harvest liquidation at Step 75 (+ $840 cash) and reinvesting into 6 strawberry seeds, APEX achieves $1,280 cash by Step 152. This enables advancing Land 2 expansion from Step 170 to Step 152 with a $280 safety buffer, allowing the SW quadrant to be tilled and planted 18 steps earlier. This unlocks 2 full additional strawberry harvest waves (+ $2,240 MCV), converting 68.2% of Cluster-1 ladder losses into wins across 14 distinct tournament opponents without risking solvency."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Melon Liquidity Step | Strawberry Reinvest Units | Land 2 Trigger Step | Cash Safety Buffer | Strategy Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-148-01`** | `96` (Control) | `0` | `170` | `$1,100` | `APEX 3.5 PROD` Control (Baseline Schedule) |
| **`CAND-148-02`** | `75` | `6` | `152` | `$1,000` | Variant C: Standard Composite Acceleration |
| **`CAND-148-03`** | `75` | `6` | `148` | `$1,000` | Variant C: Fast Land Trigger (Step 148) |
| **`CAND-148-04`** | `75` | `6` | `156` | `$1,100` | Variant C: Conservative Safety (Step 156) |
| **`CAND-148-05`** | `75` | `6` | `170` | `$1,100` | Variant A: Liquidity Conversion Only |
| **`CAND-148-06`** | `75` | `8` | `152` | `$1,000` | Variant C: Aggressive Strawberry Reinvestment |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed golden seeds x 2 seats = 100 paired matches per candidate (600 total matches) on heterogeneous opponent profiles. Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
