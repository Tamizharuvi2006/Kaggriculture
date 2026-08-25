# 🚨 SIMULATOR INCIDENT AUDIT: EXP-0136 ANIMAL LIFECYCLE & DEPLOYMENT GAP

> **Incident ID**: `INC-2026-08-15-EXP0136`  
> **Target Experiment**: `EXP-0136` (`DAY_1_COW_DOMINANCE_VS_SHEEP_ROI_REALLOCATION`)  
> **Discrepancy**: PAIRED_GPU_V2.5 reported **100.0% WR / +$32,920 MCV**, but Official Gate 1 reported **50.0% WR / +$0 MCV**.  
> **Status**: ROOT CAUSE ISOLATED & DETERMINISTICALLY PROVEN.

---

## 🔍 1. Root Cause Breakdown: The Physical Animal Deployment Chain

In `kaggle_environments v1.32.6`, animal production is **not an abstract market state**. It requires a physical multi-step spatial transport pipeline:

```
[OFFICIAL KAGGLE_ENVIRONMENTS V1.32.6 PHYSICAL ANIMAL PIPELINE]

  Step 0: BUY_ANIMAL (Animal stored in private shed inventory)
            │
            ▼
  Step 1: BUILD_PASTURE (Farmer constructs 4x4 pasture tile on farm grid)
            │
            ▼
  Step 2: PICKUP_ANIMAL (Worker/Farmer walks to shed and executes ['PICKUP', 'COW', 1])
            │
            ▼
  Step 3: WALK_TO_PASTURE (Worker moves across 10x10 farm grid: NORTH/WEST)
            │
            ▼
  Step 7: PLACE_ANIMAL (Worker executes ['PLACE', 'COW'] onto physical pasture tile)
            │
            ▼
  Step 9+: FEED & MILKING (Cow is situated in pasture tile, eats wheat, produces milk)
```

---

## 🔬 2. The Exact Divergence Point

```
========================================================================================================
[DIFFERENTIAL REPRODUCTION: PAIRED_GPU_V2.5 vs KAGGLE_ENVIRONMENTS V1.32.6]
========================================================================================================
  Stage / Action              Official kaggle_environments          PAIRED_GPU_V2.5
--------------------------------------------------------------------------------------------------------
  1. BUY_ANIMAL COW 5         Stores 5 cows in shed inventory       Increments state tensor `cows = 5`
  2. BUILD_PASTURE            Constructs Pasture at tile (4,4)      Implicit pasture flag = True
  3. Worker PICKUP & PLACE    Requires 6 specific movement steps    BYPASSED (Assumed instant deployment)
  4. Baseline Worker Script   Hardcoded to:                         N/A (No worker spatial loop)
                              - Step 2: ['PICKUP', 'SHEEP', 1] (FAILS: 0 sheep in shed)
                              - Step 8: ['PLACE', 'SHEEP']     (FAILS: holding nothing)
                              - 3 cows remain in shed forever!
  ------------------------------------------------------------------------------------------------------
  5. Realized Milk Cycles     Candidate has 2 active cows           Candidate has 5 active cows
                              (Identical to baseline)               (+$32,920 theoretical milk revenue)
  6. Final Replay Outcome     50.0% WR / +$0 MCV (GATE 1 FAIL)     100.0% WR / +$32,920 MCV (SCREEN FAIL)
========================================================================================================
```

---

## ⚖️ 3. Concrete Infrastructure & Governance Conclusions

1. **Why V2.5 Passed Initial Parity**: Initial parity testing evaluated fixed golden trajectories where worker movements and animal deployments were in 100% lockstep with baseline actions. The abstraction gap only manifested when a **policy intervention changed market animal purchases without modifying the corresponding worker spatial transport sub-routines**.
2. **The Golden Rule Proven**: This incident completely vindicates our governance hierarchy:
   $$\text{Fast Simulator (Search Funnel)} \longrightarrow \mathbf{\text{Official Gate 1 (Truth Authority)}} \longrightarrow \mathbf{\text{Gate 2/3/4}}$$
   Because Gate 1 stood as the immutable judge, zero corrupted candidates reached production.
3. **Corrective Action**:
   - `PAIRED_GPU_V2.5` must model physical worker pickup and pasture placement constraints for animal interventions.
   - Any future animal portfolio candidate must modify both the market purchase order **and the physical worker movement pathing**.
