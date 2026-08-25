# 🧠 RESEARCH COUNCIL CYCLE #7: META-AUDIT & ADAPTIVE QUEUE

> **Audit Scope**: 807 Tournament Matches, 46 Ladder Loss Seeds, 86 Trajectories, and Complete `EXP-0113` through `EXP-0141` Ledger.  
> **Strategic Alignment**: Focus on validated dynamic overlay parameters in `submission_candidate_apex35.py` (`adaptive_capital_priority`, `cash_reserve`, `interference_targeted_sort`).  
> **Permanently Excluded**: All 17 closed/invalid families.

---

## 📊 1. Top 5 Ranked Opportunities

| Rank | Experiment ID | Hypothesis Archetype | Verified Baseline Occurrence | Causal Mechanism | Expected MCV Lift | Observability | GPU Screening? |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **#1** | **`EXP-0142`** | **`ADAPTIVE_CAPITAL_EXPANSION_PRIORITY_ACTIVATION`** | `adaptive_capital_priority = False`. | Dynamically advances Land 2 and animal purchases when opponent expands early. | **`+$1,400 to +$2,800`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#2** | **`EXP-0144`** | **`DYNAMIC_CASH_RESERVE_PHASE_SCALING`** | `cash_reserve = 150` static floor. | Scales cash reserve dynamically ($0 opening -> $150 mid -> $0 late). | **`+$600 to +$1,200`** | 100% Legal | **YES (PAIRED_GPU_V2.5)** |
| **#3** | **`EXP-0143`** | **`TARGETED_MARKET_INTERFERENCE_SORTING`** | `interference_targeted_sort = False`. | Sells commodities visible in opponent's ripening pipeline before opponent can sell. | **`+$500 to +$1,100`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#4** | **`EXP-0146`** | **`DYNAMIC_WHEAT_SQUEEZE_ON_HERD_EXPANSION`** | `interference_wheat_squeeze = False`. | Drives up feed price on large opponent herds (8+ cows). | **`+$400 to +$900`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |
| **#5** | **`EXP-0145`** | **`INTERFERENCE_EXPOSURE_THRESHOLD_TUNING`** | `interference_min_exposure = 0.50`. | Tunes exposure trigger sensitivity in [0.25, 0.35, 0.50, 0.65]. | **`+$350 to +$800`** | 100% Public | **YES (PAIRED_GPU_V2.5)** |

---

## 🔍 2. Deep Dive: Top Recommended Primary Target (`EXP-0142`)

```
========================================================================================================
[EXP-0142: ADAPTIVE CAPITAL EXPANSION PRIORITY ACTIVATION]
========================================================================================================
  • Baseline Setting             : STRATEGY['adaptive_capital_priority'] = False
  • The Competitive Vulnerability: In ladder losses against aggressive bots (V18, Radiant, Venks), 
                                   the opponent expands land and herd size by Days 4–8. APEX 3.5 sits 
                                   on fixed timing, allowing the opponent to establish an insurmountable lead.
  • Proposed Optimization        : Enable adaptive capital priority with validated scaling:
                                   - adaptive_capital_priority = True
                                   - adaptive_capital_max_day = 12
                                   - adaptive_capital_animal_lead = 2
                                   - adaptive_capital_land_lead = 1
  • Expected Impact              : Dynamically closes the expansion gap against aggressive opponents, 
                                   recovering +$1,400 to +$2,800 MCV in ladder loss seeds.
========================================================================================================
```

---

## ⚖️ 3. Governance Status & Research Recommendation
1. `EXP-0142` directly addresses the **#1 defeat mechanism identified in the 46 ladder loss seeds** (falling behind aggressive expanding opponents).
2. It operates 100% on **legally observable public opponent land and animal counts**.
3. The Research Council recommends **`EXP-0142`** as the next primary research target.
