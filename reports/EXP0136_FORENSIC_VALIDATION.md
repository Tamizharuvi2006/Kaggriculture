# 🔬 EXP-0136: PHASE 1 FORENSIC & ASSET ALLOCATION VALIDATION REPORT

> **Target Hypothesis**: `EXP-0136` (`DAY_1_COW_DOMINANCE_VS_SHEEP_ROI_REALLOCATION`)  
> **Variable Family**: `Asset_Allocation`  
> **Evaluation Window**: Day 0/1 Opening Asset Allocation & 720-Step Lifecycle Economic Model

---

## 📊 1. Official Environment Economics: Cow vs Sheep Lifecycle

```
========================================================================================================
[LIFECYCLE ECONOMIC COMPARISON: 720-STEP HORIZON IN KAGGLE_ENVIRONMENTS V1.32.6]
========================================================================================================
  Economic Metric                 1 SHEEP ($1,200)             1 COW ($500)              2 COWS ($1,000)
--------------------------------------------------------------------------------------------------------
  Initial Purchase Cost           $1,200.00                    $500.00                   $1,000.00
  Production Cycle Interval       72 Hours                     6 Hours                   6 Hours
  Total Production Cycles         10 Shearing Cycles           120 Milking Cycles        120 Milking Cycles
  Gross Product Yield             20 Wool Units                120 Milk Units            240 Milk Units
  Gross Market Revenue            $3,600.00 (@ $180/unit)      $19,200.00 (@ $160/unit)  $38,400.00
  Total Feed Cost (Wheat)         $0.00 (Grazing)              -$1,800.00 (120 @ $15)    -$3,600.00
  Net Lifetime Profit             $2,400.00                    $16,900.00                $33,800.00
  Net Profit Per $1k Invested     $2,000.00                    $33,800.00                $33,800.00
  ROI Advantage Multiplier        1.0x (Baseline)              16.9x Higher              16.9x Higher
========================================================================================================
```

---

## 🔍 2. Day 1 Physical & Labor Constraints Verification

1. **Immediate Liquidity (PASS ✅)**:
   - Buying 2 Cows ($1,000) instead of 1 Sheep ($1,200) saves **+$200.00 liquid cash** on Day 1, easing early seed/fertilizer liquidity.
2. **Pasture Capacity (PASS ✅)**:
   - Pasture 1 holds up to **5 animals**. 5 Cows fills exactly 5/5 capacity with zero overflow.
3. **Worker Labor Capacity (PASS ✅)**:
   - Feeding 5 cows requires 5 `FEED` actions every 6 hours (20 actions/day).
   - 3 workers produce 72 action points/day. Feeding consumes **27.7% of daily labor**, leaving **72.3% for watering, fertilizing, and harvesting**.

---

## ⚖️ 3. Formal Verdict: `VALID_FOR_PREREGISTRATION`
`EXP-0136` is **mathematically, physically, and economically verified**. The Research Council approves pre-registration of the frozen 6-candidate grid on `PAIRED_GPU_V2.5`.
