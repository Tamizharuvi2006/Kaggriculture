# 🔬 EXP-0131: PHASE 1 FORENSIC & TERMINATION ACCOUNTING REPORT

> **Target Hypothesis**: `EXP-0131` (`TERMINAL_WHEAT_FEED_EXACT_CALIBRATION`)  
> **Variable Family**: `Capital_Preservation`  
> **Evaluation Window**: Steps 600 – 720 of Production Baseline Schedule & 807 Tournament Records

---

## 📊 1. Exact Accounting: Wheat Purchases vs Realized Cow Feeding

```
========================================================================================================
[TERMINAL WHEAT FEED AUDIT: STEPS 672 - 720 (FINAL 48 HOURS)]
========================================================================================================
  • Active Cow Herd Size          : 8 Cows (Constant from Step 257 to 720)
  • Remaining Milking Ticks       : 8 Ticks (Steps 678, 684, 690, 696, 702, 708, 714, 720)
  • Total Wheat Purchased Post-672: 43 Units
  • Total Wheat Fed to Cows       : 10 Units
  • Excess Unconsumed Wheat in Shed: 33 Units
  • Mean Buy Price vs Salvage Val : $18.50 (Buy) vs $10.00 (Terminal Credit)
  • Realized Net Dead Cash Loss   : $280.50 per match
========================================================================================================
```

---

## 🔍 2. Mathematical Demand Formulation

$$\text{Demand}_{\text{rem}}(t) = \max\left(0, N_{\text{cows}} \cdot \left\lfloor \frac{720 - t}{6} \right\rfloor - \text{Wheat}_{\text{shed}}(t) + \text{Buffer}\right)$$

* **The Problem**: APEX 3.5's static schedule purchases wheat in large bursts (e.g. Step 673: 15 units, Step 675: 13 units) designed for earlier game phases, leaving unconsumed units in shed at Step 720.
* **The Solution**: Clamping terminal wheat purchases to exact remaining cow feeding demand eliminates the spread loss while preserving 100% of milk production cycles.

---

## ⚖️ 3. Formal Verdict: `VALID_FOR_PREREGISTRATION`
`EXP-0131` is **verified and validated**. The Research Council approves pre-registration of the frozen bounded grid on `PAIRED_GPU_V2.5`.
