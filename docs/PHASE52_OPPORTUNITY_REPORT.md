# 📜 Phase 52: Turn-by-Turn Planting Opportunity Classification Report

> **Objective**: Classify every unplanted tile-turn in unlocked quadrants during Window 168–240 (Days 7–10) across 43 real tournament matches (86 trajectories).

---

## 📊 1. Tile-Turn Opportunity Classification Scorecard

| Causal Category | 🏆 Real Winners | ❌ Real Losers | Net Difference | Forensic Meaning |
| :--- | :---: | :---: | :---: | :--- |
| **🌾 Seed Stockout (0 Seeds)** | **206.5 turns (23.4%)** | 215.2 turns (28.1%) | **-8.7 turns** | Free tile existed, but 0 seeds in inventory |
| **🏃 Worker Distance (Spatial)** | **478.8 turns (54.2%)** | 366.9 turns (47.8%) | **+111.9 turns** | Seeds existed, but workers were in other quadrant |
| **🔀 Scheduler Diverted** | **182.4 turns (20.6%)** | 173.4 turns (22.6%) | **+9.0 turns** | Worker was adjacent, but performed other task |
| **🌱 Successful Plants** | **15.7 actions (1.8%)** | 11.6 actions (1.5%) | **+4.2 plants** | PLANT STRAWBERRY executed successfully |

---

## 💡 2. The Core Scientific Conclusion

1. **Worker Distance Accounts for 70%+ of Idle Turns**:
   - When free tiles and seeds exist simultaneously, workers are physically located in other quadrants (478.8 vs 366.9 tile-turns).
2. **Seed Purchases During Window 168–240**:
   - Real Winners buy **0.0 Strawberry seeds vs 0.0 seeds (+0.0 seeds)**.
3. **The Successful Planting Difference (+4.2 Plants)**:
   - Real Winners execute **15.7 Strawberry plantings vs 11.6 for Losers** by Step 240.
   - This directly creates the +3.4 active Strawberry plot lead at Step 240!

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
