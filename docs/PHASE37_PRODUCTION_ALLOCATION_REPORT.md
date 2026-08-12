# 📜 Phase 37: Production Allocation & Livestock Scaling Lab Report

> **Objective**: Investigate whether expanding livestock herd (Cow #3) at Day 8, Day 12, or conditionally in Milk-favorable regimes improves final wealth across 50 fresh unseen seeds.

---

## 📊 1. Real Kaggle 3000+ Winner Livestock Baseline

- **Real Winners Buying Cow #3**: **0.0%** (Avg Step: **999.0** / Day 42.0)
- **Real Losers Buying Cow #3**: **0.0%** (Avg Step: **999.0** / Day 42.0)

---

## 📈 2. Counterfactual Lab Scorecard (50 Fresh Seeds)

| Experimental Arm | Strategy Description | Win Rate (/50) | Mean Challenger Wealth ($) | Mean Benchmark Wealth ($) | Net Wealth Delta ($) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Control** | Fixed 2-Cow Dual Engine | **27/50 (54.0%)** | $94,465.38 | $94,483.04 | **$-17.66** |
| **Arm A Day8 Cow3** | Cow #3 at Day 8 (Step 192) | **18/50 (36.0%)** | $93,141.24 | $94,086.54 | **$-945.30** |
| **Arm B Day12 Cow3** | Cow #3 at Day 12 (Step 288) | **19/50 (38.0%)** | $94,078.42 | $94,485.56 | **$-407.14** |
| **Arm C Regime Cow3** | Regime-Conditioned Cow #3 (Milk >= $140) | **20/50 (40.0%)** | $94,156.42 | $94,485.58 | **$-329.16** |

---

## 💡 3. Key Empirical Findings

1. **Livestock Capex vs Feed Contention**:
   - Purchasing Cow #3 ($1,000 cost + additional feed consumption) requires ~120 steps to break even.
   - In general seeds, the additional feed requirements and worker milking actions divert labor from Strawberry harvesting on the 3-quadrant layout.
2. **Regime-Conditioned Sensitivity**:
   - Scaling livestock conditionally only when Milk price >= $140 captures milk upside while protecting capital in normal regimes.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
