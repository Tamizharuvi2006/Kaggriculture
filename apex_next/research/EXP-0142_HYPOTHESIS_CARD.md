# EXP-0142: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0142`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b8bad8fbd)  
> **Target Archetype**: `ADAPTIVE_CAPITAL_EXPANSION_PRIORITY_ACTIVATION`  
> **Sole Variable Family**: `Capital_Pacing`  
> **Evidence Source**: reports/EXP0142_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"By enabling adaptive capital priority (adaptive_capital_priority = True), APEX 3.5 dynamically reorders intra-step market orders to execute SELL orders before BUY_LAND and BUY_ANIMAL orders when the rival establishes an early land or animal lead. This guarantees that capital purchases succeed using fresh intra-step sale revenues rather than dropping due to temporary cash deficits, recovering +$1,400 to +$2,800 MCV in ladder loss seeds without perturbing physical worker movement paths."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Adaptive Capital Priority | Max Day | Animal Lead | Land Lead | Strategy Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`CAND-142-01`** | `False` (Control) | `12` | `2` | `1` | `APEX 3.5 PROD` Control (Unordered Capital Orders) |
| **`CAND-142-02`** | `True` | `12` | `2` | `1` | Standard Adaptive Capital Priority |
| **`CAND-142-03`** | `True` | `12` | `1` | `1` | High Sensitivity Priority (1 animal / 1 land lead) |
| **`CAND-142-04`** | `True` | `12` | `3` | `2` | Conservative Priority (3 animal / 2 land lead) |
| **`CAND-142-05`** | `True` | `8` | `2` | `1` | Tight Early Window (Days 1 - 8) |
| **`CAND-142-06`** | `True` | `16` | `2` | `1` | Extended Window (Days 1 - 16) |

*Total Frozen Grid*: Exactly **6 pre-registered candidate configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top candidate evaluated on **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
"""
