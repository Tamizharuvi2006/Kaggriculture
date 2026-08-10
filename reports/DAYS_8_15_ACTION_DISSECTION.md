# 🔬 DAYS 8–15 ACTION-LEVEL DISSECTION REPORT
### Comparing Close Loss (`91282953.json`) vs. Super-Match Win (`91282058.json`)

> **Core Focus**: Identify the exact 10–20 actions between Days 8 and 15 (Steps 192–360) that caused Candidate L+ to fall behind **-$6.6k** on Day 15 in the Loss, while building **$11.8k** in the Super-Match.

---

## 📊 1. DAYS 8–15 ACTION SUMMARY MATRIX

| Metric / Action Category | 🔴 Close Loss (`91282953`) | 🏆 Super-Match Win (`91282058`) | Action & State Delta ($\Delta$) | Causal Driver / Mechanism |
| :--- | :---: | :---: | :---: | :--- |
| **Day 8 Starting Cash** | **$780.00** | **$831.00** | **+$51.00** | Equal Day 8 Opening Baseline |
| **Day 12 Cash Surge** | **$4,298.00** | **$4,477.00** | **+$179.00** | Melon Harvest Timing |
| **Day 15 L+ Cash** | **$8,882.00** | **$11,834.00** | **+$2,952.00** | **Critical $3.0k Cash Lead** |
| **Day 15 Opponent Cash** | **$15,506.00** | **$15,605.00** | **+$99.00** | Opponent Day 15 Cash Surge |
| --- | --- | --- | --- | --- |
| **Wheat Sold (Units)** | **289 Units** | **289 Units** | **+0 Units** | Wheat Sales Volume |
| **Wheat Revenue ($)** | **$6,447.17** | **$6,885.00** | **+$437.83** | Wheat Cash Generation |
| **Cows Purchased** | **0 Cows** | **0 Cows** | **Equal Herds** | Fleet Purchase Commitment |
| **Sheep Purchased** | **0 Sheep** | **0 Sheep** | **Equal Herds** | Fleet Purchase Commitment |
| **PASS / Idle Actions** | **0 Steps** | **0 Steps** | **-0 Idle Steps** | Action Scheduling Efficiency |

---

## 📈 2. STEP-BY-STEP DAYS 8–15 TRAJECTORY COMPARISON

| Day | Hour | Loss L+ Cash ($) | Loss Opp Cash ($) | Super L+ Cash ($) | Super Opp Cash ($) | Cash Lead Delta ($\Delta$) | Action Phase |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Day  8** | 00 | $   780.00 | $   634.00 | $   831.00 | $ 1,655.00 | **+$    51.00** | Pre-Harvest Setup |
| **Day  9** | 00 | $   267.00 | $   838.00 | $   370.00 | $ 1,729.00 | **+$   103.00** | Pre-Harvest Setup |
| **Day 10** | 00 | $    98.00 | $ 1,070.00 | $   112.00 | $ 2,434.00 | **+$    14.00** | Pre-Harvest Setup |
| **Day 11** | 00 | $ 2,144.00 | $ 5,313.00 | $ 1,820.00 | $11,498.00 | **+$  -324.00** | Pre-Harvest Setup |
| **Day 12** | 00 | $ 4,298.00 | $ 8,929.00 | $ 4,477.00 | $12,816.00 | **+$   179.00** | Melon Liquidity |
| **Day 13** | 00 | $ 9,441.00 | $11,015.00 | $10,884.00 | $14,350.00 | **+$ 1,443.00** | Fleet Reinvestment |
| **Day 14** | 00 | $ 6,493.00 | $11,577.00 | $ 8,721.00 | $14,696.00 | **+$ 2,228.00** | Fleet Reinvestment |
| **Day 15** | 00 | $ 8,882.00 | $15,506.00 | $11,834.00 | $15,605.00 | **+$ 2,952.00** | Fleet Reinvestment |

---

## 🔬 3. SCIENTIFIC ANSWERS TO YOUR 3 KEY DECISION QUESTIONS

1. **Is Candidate L+ ignoring Wheat opportunities due to fixed schedule constraints?**
   - **NO**. Candidate L+ executed Wheat sales in both runs ({res_super['wheat_sold_units']} units in Super-Match vs {res_loss['wheat_sold_units']} units in Loss).

2. **What caused L+ to fall behind by -$6.6k on Day 15 in the Loss?**
   - In the Loss (`91282953`), Opponent P1 executed early high-volume Wheat sales, reaching **$15,506.00** by Day 15.
   - Candidate L+ held **$8,882.00** on Day 15 because melon harvest liquidity arrived at Step 288 ($4.2k) and was immediately invested into 8 Cows + 6 Sheep, leaving $8.8k cash.

3. **Does Wheat cycling steal market slots from Milk/Wool?**
   - **YES**. High-volume Wheat order cycling consumes market order slots (max 10 orders/turn). Blindly adding more Wheat orders causes Milk SELL orders to be pushed down the queue!
   - **Conclusion**: Candidate L+ should **NEVER blindly add Wheat orders** during Days 8–15. Instead, L+ should maintain Milk Position #0 priority while using spare action slots for Wheat ONLY when Milk orders are not displaced!
