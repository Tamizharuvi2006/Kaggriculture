# 📜 Phase 84: Opponent-Strength x Market-Potential 2x2 Factorial Report

> **Research Purpose**: Pristine 2x2 Factorial Experiment to decisively disentangle the **Market Potential (Seed) Effect** from the **Opponent Strength Effect**.
> **Core Architectural Rule**: The APEX 3.5 Candidate policy is **100% IDENTICAL** across all 4 cells.

---

## 📊 1. Master 2x2 Factorial Matrix Results (30 Seeds per Cell | Controlled Local Validation)

| Factorial Cell | Market Condition | Opponent Type | Our Wealth ($) | Opponent Wealth ($) | Total Economic Pie ($) | Capture Share (%) | Win Rate (%) | Mean Straw Price ($) | Mean Milk Price ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cell A** | Normal Market | Strong (APEX 3.5 Master) | **$91,221.00** | $90,822.43 | **$182,043.43** | **50.1%** | **46.7%** (14W-16L) | $155.97 | $125.78 |
| **Cell B** | High-Potential | Strong (APEX 3.5 Master) | **$92,161.67** | $91,748.47 | **$183,910.13** | **50.1%** | **53.3%** (16W-14L) | $155.35 | $127.93 |
| **Cell C** | Normal Market | Weak (1100-tier Bot)* | **$169,242.90** | $67.97* | **$169,310.87** | **99.96%** | **100.0%** (30W-0L) | $192.73 | $210.62 |
| **Cell D** | High-Potential | Weak (1100-tier Bot)* | **$171,456.37** | $61.50* | **$171,517.87** | **99.96%** | **100.0%** (30W-0L) | $194.47 | $209.78 |

*> **Note on Weak Opponent Wealth**: In Cells C and D, the weak opponent experienced catastrophic wage starvation and unpaid worker bankruptcies due to delayed Land #2/3 expansion, finishing with literally $67.97 and $61.50 (sixty-seven dollars) in final cash. APEX 3.5 captured 99.96% of the available market cash flow.*

---

## 💡 2. Causal Factorial Decomposition (Pristine Mathematical Reconciliation)

Using the four empirical cell means:
- $A = \$91,221.00$
- $B = \$92,161.67 \quad (\Delta_{\text{Market}} = +\$940.67)$
- $C = \$169,242.90 \quad (\Delta_{\text{Opponent}} = +\$78,021.90)$
- $D = \$171,456.37$

The exact two-way ANOVA decomposition sums identically to Cell D:
$$\text{Cell D} = A + (B - A) + (C - A) + (D - C - B + A) = \$91,221.00 + \$940.67 + \$78,021.90 + \$1,272.80 = \mathbf{\$171,456.37}$$

```
========================================================================================================================
Causal Factor                         | Formula Definition              | Value ($)     | Contribution | Empirical Meaning
========================================================================================================================
Baseline Cell A (Strong x Normal)     | A                               | $  91,221.00 |            - | Saturated symmetric 50/50 Nash split
1. Simple Opponent Effect (Normal)    | C - A                           | +$ 78,021.90 |        97.2% | Exploitation on normal market seeds
2. Simple Market Effect (Strong)      | B - A                           | +$    940.67 |         1.2% | Baseline price lift with strong opponent
3. Two-Way Interaction (Synergy)      | D - C - B + A                   | +$  1,272.80 |         1.6% | Super-additive compounding in Cell D
------------------------------------------------------------------------------------------------------------------------
🔥 EXACT CELL D RECONSTRUCTION        | A + (C-A) + (B-A) + Interaction | $ 171,456.37 |       100.0% | Complete mathematical identity
========================================================================================================================

Marginal Main Effects (ANOVA Mean-Difference Convention):
- Main Effect of Opponent Weakness = [(C - A) + (D - B)] / 2 = +$78,658.30
- Main Effect of Market Potential   = [(B - A) + (D - C)] / 2 = +$1,577.07
```

---

## 🔍 3. The 3 Supported Scientific Conclusions

1. **Opponent Quality Is the Overwhelming Driver of Absolute Wealth**:
   - In controlled testing, opponent weakness accounted for **+$78,021.90 to +$78,658.30** in additional wealth capture, compared to **+$940.67 to +$1,577.07** for market potential.
   - When the opponent fails to dump volume into the Town Center, market congestion disappears, prices float upward to $192–$194 Strawberry and $209–$210 Milk, and APEX 3.5 captures the entire market surplus.

2. **Symmetric Self-Play Ceiling ($91k–$92k) Is Stable**:
   - Against an equally strong, non-blundering opponent (Cells A & B), both bots compete for the same clearance liquidity, locking the outcome into a symmetric Nash equilibrium (~$91.2k–$92.2k).

3. **Validation Scope & Governance**:
   - This result validates APEX 3.5's exploitation capability across 60 controlled local matches (30W-0L in Cell C, 30W-0L in Cell D).
   - Real Kaggle opponents will exhibit a spectrum of behaviors (from fully saturated masters to intermediate and weak bots).
   - Therefore, the next research phase (Phase 85) must design an **Observable Telemetry & Regime Classifier** that detects opponent strength in real-time without sacrificing the strong-opponent floor.

---

## 🏛️ Governance, Baseline Protection & Code Integrity

- 🛡️ **Ref 55249106 (V4.1 Master Champion)**: **100% PROTECTED & UNTOUCHED**.
- 📦 **Ref 55411304 (APEX 3.0 Benchmark)**: Historical benchmark preserved.
- 🚀 **Ref 55421857 (APEX 3.3 Challenger)**: Clearance Preemption Challenger live on Kaggle.
- 🔒 **APEX 3.5 Candidate (`submission_candidate_apex35.py`)**: **FROZEN LOCALLY**. Zero Kaggle uploads executed.
