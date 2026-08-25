# 🧠 RESEARCH COUNCIL CYCLE #11: META-AUDIT & ACTIVE LIQUIDITY ENGINE QUEUE

> **Audit Scope**: 807 Tournament Matches, 46 Ladder Loss Seeds, 86 Trajectories, and Complete `EXP-0113` through `EXP-0146` Ledger.  
> **Key Insight**: Targeting the active runtime parameters in `agent()`'s **Dual-Regime Liquidity & Price Filtering Engine** (`safe_buffer` thresholds for Quadrants 1 & 2, `p_straw` and `p_milk` peak triggers, and momentum filters).  
> **Permanently Excluded**: All 21 closed/invalid families.

---

## 📊 1. Top 5 Ranked Opportunities

| Rank | Experiment ID | Hypothesis Archetype | Verified Baseline Occurrence | Causal Mechanism | Expected MCV Lift | Observability | GPU Screening? |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`EXP-0147`** | **`SAFE_BUFFER_QUADRANT_2_CALIBRATION`** | `safe_buffer = 2200` in Quadrant 2 (`agent()` line 4523). | Calibrating safe_buffer in [$1600, $1800, $2000, $2200] prevents premature strawberry/milk dumps, capturing peak prices while keeping Land 3 solvent at Step 261. | **`+$450 to +$950`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#2** | **`EXP-0149`** | **`GENTLE_REBOUND_STRAWBERRY_MOMENTUM_THRESHOLD`** | `p_straw >= 140.0` selling trigger (`agent()` line 4551). | Calibrates peak selling threshold in [125, 130, 135, 140, 145] to capture top-of-cycle prices. | **`+$350 to +$750`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#3** | **`EXP-0150`** | **`SAFE_BUFFER_QUADRANT_1_CALIBRATION`** | `safe_buffer = 1100` in Quadrant 1 (`agent()` line 4521). | Calibrates safe_buffer in [$900, $1000, $1100, $1200] to optimize Day 2-5 strawberry holding. | **`+$300 to +$650`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#4** | **`EXP-0151`** | **`GENTLE_REBOUND_MILK_MOMENTUM_THRESHOLD`** | `p_milk >= 115.0` selling trigger (`agent()` line 4554). | Calibrates milk selling trigger in [100, 105, 110, 115, 120]. | **`+$250 to +$550`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#5** | **`EXP-0152`** | **`REBOUND_VELOCITY_FILTER_SENSITIVITY`** | `v_straw < 0` selling filter (`agent()` line 4545). | Calibrates velocity slope threshold in [0.0, -1.0, -3.0, -5.0]. | **`+$200 to +$450`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |

---

## 🔍 2. Deep Dive: Top Recommended Primary Target (`EXP-0147`)

```
========================================================================================================
[EXP-0147: SAFE BUFFER QUADRANT 2 CALIBRATION]
========================================================================================================
  • Baseline Setting             : safe_buffer = 2200.0 in Quadrant 2 (Steps 170–260)
  • Active Execution Path        : Evaluated on EVERY SINGLE STEP in agent()
  • The Causal Inefficiency      : In Quadrant 2 (Steps 170 to 220), when cash is between $1,400 and $2,100, 
                                   the engine treats the farm as "cash constrained" and executes unconditional 
                                   strawberry/milk dumps, selling at intermediate or depressed prices.
                                   However, Land 3 ($2,000) is not scheduled until Step 261 (40–90 steps later!).
  • Proposed Optimization        : Calibrate safe_buffer across [$1,600, $1,800, $2,000, $2,200] so that 
                                   early in Quadrant 2, the engine holds inventory to capture peak rebound 
                                   prices ($140+ for Strawberries, $115+ for Milk), while still guaranteeing 
                                   $2,000 cash before Step 261.
  • Expected Impact              : +$450 to +$950 MCV lift across all 807 matches.
========================================================================================================
```

---

## ⚖️ 3. Governance Status & Research Recommendation
1. `EXP-0147` directly tunes the **active, step-by-step liquidity gating threshold in `agent()`** that controls every strawberry and milk sale during Steps 170–260.
2. It satisfies all 6 criteria: **Real Baseline Occurrence**, **Real Causal Mechanism**, **Competitive Win Condition**, **100% Legal Internal State**, **Physical Lifecycle Representability**, and **Not Already Falsified**.
3. The Research Council recommends **`EXP-0147`** as the next primary research target.
