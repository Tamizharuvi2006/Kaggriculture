# EXP-0129: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0129`  
> **Target Baseline**: `APEX-3.5-PROD` (submission.py, SHA256 78738c1b...)  
> **Target Archetype**: `DYNAMIC_SLIPPAGE_AWARE_BATCHING`  
> **Sole Variable Family**: `Market_Execution` (Single-variable execution optimization)  
> **Evidence Source**: reports/EXP0129_FORENSIC_VALIDATION.json

---

## 1. Formal Mechanism Hypothesis

> *"When liquidating mature commodity inventory (Strawberries / Milk), splitting large inventory dumps (V >= V_split) into bounded micro-batches of size Q_cap across consecutive timesteps (provided price momentum is non-negative, v >= 0) mitigates non-linear market volume slippage (1 - 0.005 * V^0.75), capturing an estimated +$1,200 to +$1,800 MCV without altering high-level crop schedules, animal investments, or land expansion pacing."*

---

## 2. Frozen Bounded Parameter Grid

| Candidate ID | Split Trigger (V_split) | Max Batch Cap (Q_cap) | Min Momentum (v_min) | Strategy Description |
| :--- | :---: | :---: | :---: | :--- |
| **`CAND-129-01`** | `N/A` (Control) | `No Cap` | `N/A` | `APEX 3.5 PROD` Control (Dump 100% of shed) |
| **`CAND-129-02`** | `6 Units` | `4 Units` | `0.0` | Primary Slippage Cap (V >= 6 -> Cap 4, v >= 0) |
| **`CAND-129-03`** | `8 Units` | `4 Units` | `0.0` | High-Volume Cap (V >= 8 -> Cap 4, v >= 0) |
| **`CAND-129-04`** | `6 Units` | `3 Units` | `0.0` | Tight Micro-Batch (V >= 6 -> Cap 3, v >= 0) |
| **`CAND-129-05`** | `8 Units` | `6 Units` | `0.0` | Moderate Cap (V >= 8 -> Cap 6, v >= 0) |
| **`CAND-129-06`** | `6 Units` | `4 Units` | `-1.0` | Lenient Momentum Cap (V >= 6 -> Cap 4, v >= -1) |

*Total Frozen Grid*: Exactly **6 structured configurations**.

---

## 3. Screening & Promotion Protocol
1. **PAIRED_GPU_V2.5 Screening Funnel**: Screen across 50 fixed seeds x 2 seats = 100 paired matches per candidate (600 total matches). Filter: WinRate_paired >= 55.0% AND Delta_MCV > $0.00.
2. **Official Reference Authority**: Top surviving candidate is submitted to **Gate 1 Exact Replay on kaggle_environments v1.32.6** across the 46 real ladder loss seeds (92 matches).
3. **Governance Contract**: If Gate 1 WinRate < 60.0% -> Mark FALSIFIED_GATE_1 and STOP immediately.
