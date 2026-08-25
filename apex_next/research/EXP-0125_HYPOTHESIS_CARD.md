# EXP-0125: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0125`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `OPPONENT_PUBLIC_FIELD_RIPE_CROP_FRONT_RUNNING`  
> **Sole Variable Family**: `Market_Reflexivity` (Strict single-variable isolation)  
> **Evidence Source**: reports/EXP0125_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"When inspecting the opponent's public farmland grid (`obs['farms'][1]['tiles']`), if the opponent has **>= K_ripe ripe strawberry tiles** (predicting an imminent opponent harvest and market dump with 91.5% probability), and APEX currently holds **>= Q_min strawberries** in its shed, APEX triggers **immediate pre-emptive liquidation on Step t**, capturing top-of-cycle market prices (+$20.60/unit advantage) before the opponent's subsequent dump depresses the shared order book."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Opponent Ripe Threshold (K_ripe) | APEX Min Inventory (Q_min) | Price Drop Gate (P_min) | Strategy Description |
| :--- | :---: | :---: | :---: | :--- |
| **`CAND-125-01`** | `N/A` (Control) | `N/A` | `N/A` | `APEX 3.5 PROD` Control (No Opponent Reflexivity) |
| **`CAND-125-02`** | `4 Tiles` | `2 Units` | `$110.0` | Primary Front-Runner (K=4, Q=2) |
| **`CAND-125-03`** | `3 Tiles` | `2 Units` | `$110.0` | Aggressive Early Front-Runner (K=3, Q=2) |
| **`CAND-125-04`** | `5 Tiles` | `2 Units` | `$110.0` | Conservative Front-Runner (K=5, Q=2) |
| **`CAND-125-05`** | `4 Tiles` | `4 Units` | `$110.0` | High-Batch Front-Runner (K=4, Q=4) |
| **`CAND-125-06`** | `4 Tiles` | `2 Units` | `$120.0` | High-Price Filtered Front-Runner (K=4, P >= 120) |

*Total Frozen Grid*: Exactly **6 structured configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top surviving candidate is submitted to **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
