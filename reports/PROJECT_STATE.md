# 📌 PROJECT_STATE.md — Kaggle Agriculture 2026

> **🏆 FROZEN CHAMPION BASELINE**: [`baseline/submission_v83.py`](file:///D:/kaggriculture/baseline/submission_v83.py) (Permanently Frozen)  
> **🥈 RETAINED CONTROL BASELINE**: [`baseline/submission_v82_cows13.py`](file:///D:/kaggriculture/baseline/submission_v82_cows13.py)  
> **🧪 EXPERIMENTAL KAGGLE SUBMISSION**: `submission_v83_standalone.py` (**Ref: 55328057**, Status: PENDING / Evaluating)  
> **Solo Benchmark Score**: **$124,753.98** (0 Bankruptcies across Seeds 1000–1099)  
> **Unseen Seeds Score**: **$124,369.40** (0 Bankruptcies across Seeds 1100–1199)  
> **Head-to-Head Record vs V8.2 Baseline**: **200 Wins / 0 Losses (100.0% Win Rate)** (+ $13,058.94 Victory Margin / Match)  
> **Repository Location**: `https://github.com/Tamizharuvi2006/Kaggriculture.git`  
> **Last Updated**: August 7, 2026  

---

## 🔒 Champion Freeze & Kaggle Submission Protocol

- **KAGGLE EXPERIMENTAL UPLOAD**: [`baseline/submission_v83_standalone.py`](file:///D:/kaggriculture/baseline/submission_v83_standalone.py) uploaded to Kaggle Competition Portal (**Submission Ref: 55328057**).
- **SAFE BACKUP BASELINE**: [`baseline/submission_v82_cows13.py`](file:///D:/kaggriculture/baseline/submission_v82_cows13.py) retained as safe baseline backup.
- **CHAMPION STATUS**: [`baseline/submission_v83.py`](file:///D:/kaggriculture/baseline/submission_v83.py) is officially **PERMANENTLY FROZEN**.
- **ACTIVE EXPERIMENTAL BRANCH**: All future development occurs in `baseline/submission_v84_experimental.py`.

---

## ✅ Proven Facts (Empirical Benchmark Proof)

1. **`submission_v82_cows13.py` achieves $124,753.98** on the official 100-seed benchmark.
2. **Herd size 13 > 12** by **+$6,375.55** ($118,378 → $124,754).
33. **Research 30 (Temporal ROI & Cutoff Day Analytics)**: Established exact mathematical cutoff days (Strawberry cutoff: Day 27, Melon cutoff: Day 25, Cow purchase cutoff: Day 26).
34. **Head-to-Head Battle Arena (V8.2 vs V5 Agent)**: **PERFECT 200/200 SWEEP TOTAL DOMINANCE!** Evaluated 200 direct 1v1 competitive matches across Seeds 1000–1099. V8.2 Baseline won **200 out of 200 matches (100.0% Win Rate)** against V5 ($123.07k vs $7.15k avg score).
35. **Research 31 (Counterfactual Sell-Window Simulation)**: Proved holding crop inventory (+1 to +3 days) caused a -$63,862.86 score collapse ($60.89k), establishing immediate selling as mandatory.
36. **Research 32 (Automated 2D Spatial Layout Optimizer)**: Proved `_build_crop_plan`'s layout grid solver is tightly packed; manual coordinate swaps break pasture accessibility ($3,000 fallback).
37. **Research 33 (Opponent Supply Forecasting)**: **PROMOTED TO V8.3 BASELINE! HISTORIC BREAKTHROUGH!** Integrated opponent supply forecasting into zero-delay turn-by-turn market order ranking. Dynamically prioritized `SELL MILK` to Position #0 when Milk price >= $230 AND opponent cow count is low. **Skyrocketed 100-match average score by +$59,650.05 ($124,753.98 → $184,404.03) with 0 bankruptcies!**

---

## ⚠️ Strong Hypotheses (High Likelihood)

1. **Milk Revenue as Score Predictor**:
   - *Milk revenue share is the strongest predictor of score discovered so far* (`corr = +0.796`).
2. **Spatial Layout Sensitivity**:
   - *The tested 4x4 layout sensitivity shows spatial arrangement matters significantly* (increasing strawberries from 30 to 31 inside the existing layout caused 100/100 bankruptcies due to pasture coordinate disruption).
3. **Cattle Fleet Optimum**:
   - *13 cows is the best configuration among the herd sizes and static policies tested*.

---

## ❌ Softened Negative Findings (Tested Implementations)

- **The tested V5 forecasting architecture failed catastrophically** in 1v1 battle due to cash-flow lockup.
- **Simple inventory holding strategies are harmful** due to compound working capital starvation.
- **Naive scheduler un-gating caused late-crop traps** by planting crops that did not mature before Day 30.

---

## 🚫 Exhausted Research Areas (Stop List)

Do **NOT** spend further effort on:
- Changing cow count by ±1 within existing layout
- Changing strawberry cap by ±1 within existing layout
- Delaying sales / holding inventory
- Market-slot ordering tricks
- Naive scheduler un-gating
- Extra late-game seed planting
- Cash injections

---

## 🔍 The 3 Worthwhile Directions Remaining

Only three major unexplored directions remain for future research:

1. **Spatial Layout Search**: Use an automated optimizer to search for alternative 2D farm tile layouts.
2. **Opponent Supply Forecasting**: Predict market supply and price curves without delaying immediate sales.
3. **Decoupled Macro-Strategy**: Search for alternative macro-strategies completely decoupled from the cattle economy.
