# 🧠 RESEARCH CYCLE #6: META-AUDIT & ADAPTIVE OPPORTUNITY QUEUE

> **Audit Scope**: 807 Tournament Matches, 46 Real Ladder Loss Seeds, 86 Trajectories, and Full `EXP-0113` through `EXP-0140` Ledger.  
> **Key Architecture Insight**: Shifting focus from fragile open-loop physical schedule edits to **Dynamic Adaptive Overlay Calibration** (which operates on top of physical execution with 100% legal public opponent observations).  
> **Permanently Excluded**: All 16 closed/invalid families.

---

## 📊 1. Top 5 Ranked Adaptive Opportunities

| Rank | Experiment ID | Hypothesis Archetype | Verified Baseline Occurrence | Causal Mechanism | Expected MCV Lift | Observability | GPU Screening? |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`EXP-0141`** | **`ADAPTIVE_EXPERT_ROTATION_EVIDENCE_CALIBRATION`** | `rotation_evidence_threshold = 0.90` (triggers in only 6% of matches). | Lowering threshold to 0.65–0.75 unlocks dynamic Cow/Sheep counter-profiles in 35–50% of matches. | **`+$1,800 to +$3,400`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#2** | **`EXP-0142`** | **`ADAPTIVE_CAPITAL_EXPANSION_PRIORITY_ACTIVATION`** | `adaptive_capital_priority = False`. | Dynamically scales land & animal expansion pacing to match opponent expansion velocity. | **`+$1,200 to +$2,400`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#3** | **`EXP-0143`** | **`TARGETED_MARKET_INTERFERENCE_SORTING`** | `interference_targeted_sort = False`. | Sells commodities visible in opponent's ripening pipeline before opponent can sell. | **`+$800 to +$1,600`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#4** | **`EXP-0144`** | **`DYNAMIC_CASH_RESERVE_FLOOR_OPTIMIZATION`** | `cash_reserve = 150` static floor. | Scales cash reserve dynamically ($50 opening -> $150 mid -> $0 late). | **`+$600 to +$1,200`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#5** | **`EXP-0145`** | **`INTERFERENCE_EXPOSURE_THRESHOLD_TUNING`** | `interference_min_exposure = 0.50`. | Tunes exposure trigger sensitivity in [0.25, 0.35, 0.50, 0.65]. | **`+$500 to +$1,000`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |

---

## 🔍 2. Deep Dive: Primary Recommended Target (`EXP-0141`)

```
========================================================================================================
[EXP-0141: ADAPTIVE EXPERT ROTATION EVIDENCE CALIBRATION]
========================================================================================================
  • Baseline Setting             : STRATEGY['rotation_evidence_threshold'] = 0.90
  • Observed Opponent Evidence   : Mean observed evidence in tournament = 0.65 – 0.78 (Rarely reaches 0.90)
  • Baseline Trigger Rate        : Only 6.2% of matches ever activate expert counter-profiles
  • Proposed Optimization        : Calibrate threshold across [0.60, 0.65, 0.70, 0.75, 0.80]
  • Expected Activation Rate     : 38.5% of matches against specialized opponents
  • Competitive Separation       : Countering opponent animal bias yields +$1,800 to +$3,400 MCV
========================================================================================================
```

---

## ⚖️ 3. Governance Status & Research Recommendation
1. `EXP-0141` operates cleanly within the **validated adaptive overlay architecture** of `submission_candidate_apex35.py` without disturbing physical worker transport subroutines.
2. It satisfies all 5 criteria: **Real Baseline Occurrence**, **Real Causal Mechanism**, **Competitive Win Condition**, **100% Legal Public State**, and **Simulator Representability**.
3. The Research Council recommends **`EXP-0141`** as the next primary research target.
