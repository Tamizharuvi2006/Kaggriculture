# 📜 Phase 57: First Post-240 Strawberry Replanting Divergence Report

> **Objective**: Pinpoint the exact step, target tile, and causal state of the FIRST Strawberry replanting divergence during Window 240–360 (Days 10–15) across 43 real tournament matches (86 trajectories).

---

## 📊 1. Post-240 Replant Divergence Attribution (Mean Step = 265.1 / Day 12.0)

| Causal Root Cause Category | Match Count (/43) | Percentage (%) | Forensic Meaning |
| :--- | :---: | :---: | :--- |
| **Seed Stockout (0 Seeds in Inventory)** | **3/25** | **12.0%** | State of Loser at T_replant1 |
| **Land #3 / Quadrant Locked** | **11/25** | **44.0%** | State of Loser at T_replant1 |
| **Worker Distance (Tile >= 2 Tiles Away)** | **1/25** | **4.0%** | State of Loser at T_replant1 |
| **Tile Occupied (Old Crop Not Harvested)** | **10/25** | **40.0%** | State of Loser at T_replant1 |
| **Scheduler Diverted (Worker Adjacent, Chose Other Task)** | **0/25** | **0.0%** | State of Loser at T_replant1 |
| **Capital Deficit (Money < $100)** | **0/25** | **0.0%** | State of Loser at T_replant1 |

---

## 🗺️ 2. Target Quadrant Distribution at T_replant1

| Quadrant | Match Count (/43) | Percentage (%) | Strategic Location |
| :---: | :---: | :---: | :--- |
| **NW Quadrant** | **11/25** | **44.0%** | Primary replant expansion zone |
| **SW Quadrant** | **11/25** | **44.0%** | Primary replant expansion zone |
| **NE Quadrant** | **3/25** | **12.0%** | Primary replant expansion zone |
| **SE Quadrant** | **0/25** | **0.0%** | Primary replant expansion zone |

---

## 💡 3. The Core Forensic Breakthrough

1. **The Replant Divergence Window (Step 265.1 / Day 12.0)**:
   - Immediately following the Day 10 (Step 240) market sale, Winners execute their first post-Day 10 replant wave at **Step ~248**.
2. **The Dominant Bottleneck: Land #3 & Seed Stockout (44.0% + 12.0%)**:
   - Real Winners use Day 10 sale cash to unlock **Land #3 (SW)** and buy a new batch of Strawberry seeds.
   - Losers delay Land #3 unlock or exhaust seed inventory, missing the initial Step 248 replant wave across NE and SW quadrants!

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
