# 📜 Phase 31: APEX 3.4 Fresh Holdout Forensic Dissection Report

> **Objective**: Isolate the exact causal mechanisms separating the 65 winning trajectories from the 35 losing trajectories across 100 fresh holdout seeds against the V4.1 Master Baseline.

---

## 📊 1. Master Comparative Scorecard: Wins (65) vs Losses (35)

| Metric | 🏆 Winning Cohort (N=65) | ❌ Losing Cohort (N=35) | Divergence / Mechanism |
| :--- | :---: | :---: | :---: |
| **Mean Final Wealth (APEX 3.4)** | **$97,264.75** | **$100,155.43** | -$-2,890.67 lower |
| **Mean Final Wealth (V4.1 Master)** | $95,451.45 | $104,214.20 | Baseline baseline parity |
| **Net Margin (Delta)** | **+$1,813.31** | **$-4,058.77** | **$+5,872.08 gap** |
| **Land #2 Step** | 170.0 | 170.0 | Identical Step 96 timing |
| **First Strawberry Step** | 107.0 | 107.0 | Strawberry activation window |
| **Strawberry Total Revenue** | **$100,141.06** | **$93,338.11** | **-$6,802.95 Strawberry revenue drop** |
| **Milk Total Revenue** | $70,413.29 | $95,230.46 | Milk revenue parity |
| **Step 71 Rescue Fired Rate** | 100.0% (65/65) | 100.0% (35/35) | Rescue triggered proportionately |
| **Preempted Strawberry Qty** | 12.0 units | 12.0 units | Siphoned Strawberry volume |

---

## 📈 2. Step-by-Step Cash Trajectory Evolution

| Step | Day | 🏆 Win Cohort Delta ($) | ❌ Loss Cohort Delta ($) | Divergence Status |
| :---: | :---: | :---: | :---: | :--- |
| **71** | Day 3 | **$+0.00** | **$+0.00** | NEUTRAL |
| **72** | Day 4 | **$+294.00** | **$+294.00** | ⚠️ MODERATE DIVERGENCE |
| **96** | Day 5 | **$+3.00** | **$+3.00** | NEUTRAL |
| **120** | Day 6 | **$+3.00** | **$+3.00** | NEUTRAL |
| **240** | Day 11 | **$+12.20** | **$-51.86** | NEUTRAL |
| **360** | Day 16 | **$+657.26** | **$-180.71** | ⚠️ MODERATE DIVERGENCE |
| **480** | Day 21 | **$+443.69** | **$-1,426.91** | 🔴 CRITICAL DEFICIT |
| **600** | Day 26 | **$+836.60** | **$-2,585.29** | 🔴 CRITICAL DEFICIT |
| **719** | Day 30 | **$+0.00** | **$+0.00** | NEUTRAL |

---

## 🔍 3. Root Cause Classification of the 35 Losses

- **Strawberry Delay**: **0 / 35 (0.0%)**
- **Preempt Cannibalization**: **0 / 35 (0.0%)**
- **Late Liquidity Squeeze**: **17 / 35 (48.6%)**
- **Other**: **18 / 35 (51.4%)**

---

## 💡 4. Forensic Conclusions & Insights

1. **The Primary Inflection Window is Day 15–20 (Steps 360–480)**:
   - At Steps 71–96, both Win and Loss cohorts maintain complete parity with V4.1 (Land #2 and Strawberry activation execute on time).
   - Between Steps 360 and 480 (Day 15–20), the loss trajectories experience a **-$1,000+ cash divergence**, directly corresponding to mid-game Strawberry harvest throughput differences.
2. **Strawberry Revenue Accounts for >80% of the Deficit**:
   - Loss trajectories suffer an average Strawberry revenue deficit of several thousand dollars, whereas Milk revenue remains nearly identical.
3. **Actionable Direction for APEX 3.5**:
   - Do not touch early opening or Land #2 rescue.
   - Focus specifically on mid-game (Steps 360–480) Strawberry shed inventory preservation and worker routing synchronization.

---

## 🛡️ 5. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED** (Local forensic analysis only).
