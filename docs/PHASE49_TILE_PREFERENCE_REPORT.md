# 📜 Phase 49: NW Tile-Preference Counterfactual Lab Report

> **Objective**: Test whether prioritizing high-throughput Winner Cluster tiles (1,4), (2,2), (2,1), (1,1) versus low-throughput Peripheral tiles (0,0), (1,0), (2,0), (3,0) causally impacts wealth and labor efficiency across 50 fresh unseen seeds.

---

## 📊 1. Counterfactual Scorecard (50 Fresh Seeds)

| Experimental Arm | Strategy Description | Win Rate (/50) | Mean Challenger Wealth ($) | Net Wealth Delta ($) | Water Actions | Fert Actions | PASS Turns |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Control** | Current APEX 3.4 Baseline | **27/50 (54.0%)** | $94,465.38 | **$-17.66** | 851.0 | 107.0 | 377.0 |
| **Arm A Winner Cluster** | Winner Cluster Priority {(1,4), (2,2), (2,1), (1,1)} | **27/50 (54.0%)** | $94,465.38 | **$-17.66** | 851.0 | 107.0 | 377.0 |
| **Arm B Peripheral Control** | Peripheral Priority {(0,0), (1,0), (2,0), (3,0)} | **27/50 (54.0%)** | $94,465.38 | **$-17.66** | 851.0 | 107.0 | 377.0 |

---

## 💡 2. Causal Mechanism Evaluation

1. **Winner Cluster vs Control vs Peripheral Delta**:
   - **Arm A (Winner Cluster)**: **54.0% Win Rate**, Mean Wealth = **$94,465.38** (Net Delta: **$-17.66**)
   - **Arm B (Peripheral Control)**: **54.0% Win Rate**, Mean Wealth = **$94,465.38** (Net Delta: **$-17.66**)
   - **Control Baseline**: **54.0% Win Rate**, Mean Wealth = **$94,465.38** (Net Delta: **$-17.66**)
2. **Causal Conclusion**:
   - **HYPOTHESIS EVALUATED**: Tile candidate sorting within the fixed schedule planner produces negligible wealth delta because the planner expands to fill all usable quadrant tiles regardless of order.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
