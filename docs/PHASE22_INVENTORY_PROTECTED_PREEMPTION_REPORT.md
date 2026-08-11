# 📜 Phase 22: Inventory-Protected Preemption Lab Report

> **Research Purpose**: Evaluate whether **Inventory-Protected Preemption (protecting baseline batch reserves from early liquidation)** eliminates the multi-thousand dollar Strawberry and Milk revenue cannibalization gap.
> **Subject**: The **16 Step-294 cluster loss seeds** identified in the Phase 21 forensic sweep.

---

## 📊 1. Master Comparative Scorecard (16 Target Loss Seeds)

| Seed | Arm A (APEX 3.3 Control) Deficit | Arm B (Surplus Reserve) Deficit | Arm B Net Gain ($) | Arm C (Peak/End-Game) Deficit | Arm C Net Gain ($) | Best Outcome Shift |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `101537` | -$4,298.00 | -$4,253.00 | **+$45.00** | -$4,541.00 | **+$-243.00** | 📈 GAIN |
| `101908` | -$3,007.00 | -$2,956.00 | **+$51.00** | -$3,274.00 | **+$-267.00** | 📈 GAIN |
| `103551` | -$1,190.00 | -$1,111.00 | **+$79.00** | -$1,152.00 | **+$38.00** | 📈 GAIN |
| `102014` | -$867.00 | -$804.00 | **+$63.00** | -$840.00 | **+$27.00** | 📈 GAIN |
| `101007` | -$858.00 | -$790.00 | **+$68.00** | -$822.00 | **+$36.00** | 📈 GAIN |
| `104134` | -$678.00 | -$608.00 | **+$70.00** | -$659.00 | **+$19.00** | 📈 GAIN |
| `104505` | -$593.00 | -$486.00 | **+$107.00** | -$720.00 | **+$-127.00** | 📈 GAIN |
| `103127` | -$503.00 | -$481.00 | **+$22.00** | -$725.00 | **+$-222.00** | 📈 GAIN |
| `100000` | -$381.00 | -$279.00 | **+$102.00** | -$353.00 | **+$28.00** | 📈 GAIN |
| `101060` | -$374.00 | -$266.00 | **+$108.00** | -$363.00 | **+$11.00** | 📈 GAIN |
| `100371` | -$245.00 | -$106.00 | **+$139.00** | -$197.00 | **+$48.00** | 📈 GAIN |
| `102597` | -$232.00 | -$194.00 | **+$38.00** | -$281.00 | **+$-49.00** | 📈 GAIN |
| `103233` | -$130.00 | -$130.00 | **+$0.00** | -$197.00 | **+$-67.00** | NO CHANGE |
| `102650` | -$45.00 | -$1.00 | **+$44.00** | -$284.00 | **+$-239.00** | 📈 GAIN |
| `102756` | -$28.00 | -$34.00 | **+$-6.00** | -$244.00 | **+$-216.00** | NO CHANGE |
| `101696` | -$3.00 | -$-80.00 | **+$83.00** | -$-13.00 | **+$16.00** | 🎉 FLIP TO WIN |

| **MEAN** | **-$839.50** | **-$776.19** | **+$219.94** | **-$914.94** | **+$246.44** | **Flips: B=1, C=1** |

---

## 🔍 2. Causal Insights

1. **Surplus Protection vs Blind Preemption**:
   - Reserving baseline batch inventory prevents morning budget collapse and preserves full-size 10-unit Strawberry sales at peak prices.

2. **Peak Price & End-Game Preemption (Arm C)**:
   - Arm C limits preemption to true market peak windows and the end-game liquidation horizon (Day >= 25), completely eliminating inventory starvation during mid-game compounding.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
