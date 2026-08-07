# 📌 PROJECT_STATE.md — Kaggle Agriculture 2026

> **Verified Master Baseline**: [`baseline/submission_v82_cows13.py`](file:///D:/kaggriculture/baseline/submission_v82_cows13.py)  
> **Official 100-Match Score**: **$124,753.98** (0 Bankruptcies, $6,709.16 StdDev)  
> **Head-to-Head Record**: **200 Wins / 0 Losses (100.0% Win Rate)** vs V5 Agent  
> **Repository Location**: `https://github.com/Tamizharuvi2006/Kaggriculture.git`  
> **Last Updated**: August 7, 2026  

---

## 🏆 Current Best Submission

- **File**: [`baseline/submission_v82_cows13.py`](file:///D:/kaggriculture/baseline/submission_v82_cows13.py)
- **Average Score**: **$124,753.98**
- **Median Score**: **$125,877.50**
- **Worst Score**: **$106,552.00**
- **Standard Deviation**: **$6,709.16**
- **Bankruptcies**: **0 / 100**

---

## ✅ Proven Improvements

1. **Cow Frontier Optimization (`Cows = 13`)**:
   - `Cows = 12` ($118,378.43) → `Cows = 13` (**$124,753.98**), net gain of **+$6,375.55**.
   - *Conclusion*: 13 cows is the exact mathematical local optimum of the static herd configuration space.

2. **Milk-Driven Economy**:
   - **Milk Revenue Share**: **34.49%** of total farm cash flow.
   - **`corr(score, milk_rev_share)`**: **`+0.796`**
   - *Conclusion*: Daily steady milk liquidity is the single strongest economic stabilizer and revenue driver.

3. **Immediate Selling Policy**:
   - Immediate Sell (**$124,753.98**) vs Hold +1 Day (**$60,891.12**), net loss of **-$63,862.86 (-51.2% drop)**.
   - *Conclusion*: Immediate liquidity is mandatory; holding crop inventory starves working capital.

---

## ❌ Dead Research Directions (Proven Rejected)

The following 13 strategy branches have been experimentally tested and rejected across >2,500 game simulations:

- ❌ **Land Expansion (SE Quadrant)**: -$14.0k drop ($108.0k)
- ❌ **Instant Movement Oracle**: +0.00% change
- ❌ **Starting Cash Injections**: +0.00% change
- ❌ **Unlimited Seeds**: -$2.14k drop ($118.5k) / bankruptcy
- ❌ **Feed Reordering / Priority**: -$1.86k regression ($122.8k)
- ❌ **Fertilizer Deferral**: -$6.87k regression ($117.8k)
- ❌ **Dropping SELL Orders**: 100% Bankruptcy ($0.00)
- ❌ **Herd Sizes > 13 (Cows 14–16)**: -$3.8k to -$8.5k regression
- ❌ **Scheduler Un-gating**: -$7.99k regression ($116.7k)
- ❌ **Late-Game Planting**: Un-matured crop traps
- ❌ **Inventory Holding**: -$63.86k collapse ($60.89k)
- ❌ **Speculative Sell Windows**: Delayed working capital
- ❌ **Naive Opponent Forecasting**: Over-fitting speculative plans

---

## ⚠️ Important Discoveries

1. **Scheduler Omissions Exist, But 99.5% Are Harmless**:
   - 145,843 omission events logged (max streak: 136 consecutive steps).
   - However, **99.5% of omissions are unplanted Wheat seeds** intentionally ignored by the crop plan. Only 0.5% (732 steps) involved high-ROI seeds.

2. **Spatial Constraints Matter (Layout Sensitivity)**:
   - 30 Strawberries → 31 Strawberries caused **100 / 100 Bankruptcies** ($613.91 score) due to spatial pasture tile map disruption.
   - The 4x4 spatial layout for 30 Strawberries + 13 Cows is tightly packed.

3. **Stable Liquidity Dominates Complex Planning**:
   - Head-to-Head Battle: **V8.2 (200 wins / 100.0%)** vs **V5 Agent (0 wins / 0.0%)**.
   - Average score: **$123,071.19** vs **$7,146.82** (Victory margin: **+$115,924.37 per match**).

---

## 🚫 Things to Stop Researching

Do **NOT** spend further effort on:
- Changing cow count by ±1
- Changing strawberry cap by ±1
- Delaying sales / holding inventory
- Market-slot ordering tricks
- Naive scheduler un-gating
- Extra late-game seed planting
- Cash injections

---

## 🔍 Remaining Open Questions

Only four fundamental questions remain for future exploration:
1. **Is there a fundamentally superior 2D spatial farm layout?**
2. **Can opponent behavior be exploited without delaying liquidity?**
3. **Can milk production efficiency be increased without changing tile geometry?**
4. **Is there an undiscovered macro-strategy completely decoupled from the cattle economy?**
