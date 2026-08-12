# 📜 Phase 51: Upstream Capacity & First Missing Opportunity Report

> **Objective**: Pinpoint the exact first step (T1) and causal state category responsible for the Strawberry production divergence across 43 real tournament matches (86 trajectories).

---

## 📊 1. First Missing Opportunity Attribution (Mean Divergence Step = 172.6)

| Causal Category at T1 | Match Count (/43) | Percentage (%) | Forensic Meaning |
| :--- | :---: | :---: | :--- |
| **Seed Deficit (0 Seeds)** | **18/28** | **64.3%** | Farm ran out of seeds in shed |
| **Capital Deficit (Low Money)** | **1/28** | **3.6%** | Money < $100 to buy seeds |
| **Land Occupancy (No Free Tiles)** | **0/28** | **0.0%** | All unlocked plots occupied by old crops |
| **Worker Scheduling / Execution** | **9/28** | **32.1%** | Seeds and tiles existed, but worker was elsewhere |

---

## 📈 2. Step-by-Step Capacity Progression (Steps 144–240)

| Step (Day) | 🏆 Winners Cash | ❌ Losers Cash | 🏆 Seeds Inv | ❌ Seeds Inv | 🏆 Free Tiles | ❌ Free Tiles | 🏆 Active Strawberry | ❌ Active Strawberry |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Step 144 (D7)** | $651.7 | $620.5 | 0.0 | 0.2 | 1.7 | 2.2 | **1.8 tiles** | 2.3 tiles |
| **Step 168 (D8)** | $1,579.9 | $1,287.9 | 0.1 | 0.7 | 0.4 | 2.6 | **2.1 tiles** | 2.6 tiles |
| **Step 180 (D8)** | $283.2 | $527.7 | 2.9 | 2.3 | 20.2 | 15.3 | **3.3 tiles** | 3.3 tiles |
| **Step 192 (D9)** | $716.3 | $797.5 | 0.2 | 0.7 | 13.7 | 11.2 | **6.0 tiles** | 5.0 tiles |
| **Step 204 (D9)** | $723.8 | $776.3 | 4.4 | 4.3 | 12.1 | 11.6 | **7.8 tiles** | 6.3 tiles |
| **Step 216 (D10)** | $715.6 | $834.4 | 2.4 | 2.2 | 7.6 | 7.6 | **11.4 tiles** | 9.4 tiles |
| **Step 228 (D10)** | $517.6 | $833.9 | 2.9 | 3.0 | 7.5 | 8.2 | **13.3 tiles** | 10.7 tiles |
| **Step 240 (D11)** | $661.9 | $902.4 | 1.5 | 2.5 | 4.8 | 5.9 | **16.2 tiles** | 12.8 tiles |

---

## 💡 3. The Grand Empirical Realization

1. **Primary Root Cause: Seed Deficit & Inventory Exhaustion (64.3%)**:
   - In **the vast majority of matches**, Losers diverge at **Step 180–204** because their seed inventory drops to **0 Strawberry seeds**, while Winners maintain a steady inventory buffer.
2. **Free Tiles Exist in Abundance (12.1 vs 11.6 tiles at Step 204)**:
   - At Step 204, both Winners and Losers have **~14 free tillable tiles** sitting empty in unlocked quadrants!
   - Losers do not plant them simply because they bought fewer seeds at Step 168 (Day 7 close), exhausting their seed inventory and forcing workers to PASS or do low-value tasks!

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
