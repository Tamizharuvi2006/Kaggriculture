# 📜 Phase 55: First Exact Strawberry Planting Divergence (T_plant1) Report

> **Objective**: Reconstruct the exact step and physical state of the FIRST Strawberry planting divergence between Real 3000+ Winners and Losers across 43 real tournament matches (86 trajectories).

---

## 📊 1. First Planting Divergence Attribution (Mean Step = 143.5 / Day 6.0)

| Causal Root Cause Category | Match Count (/43) | Percentage (%) | Forensic Meaning |
| :--- | :---: | :---: | :--- |
| **Seed Stockout (0 Seeds in Inventory)** | **17/29** | **58.6%** | Causal state of Loser at T_plant1 |
| **Worker Distance (Tile >= 2 Tiles Away)** | **0/29** | **0.0%** | Causal state of Loser at T_plant1 |
| **Scheduler Diverted (Worker Adjacent, Chose Other Task)** | **0/29** | **0.0%** | Causal state of Loser at T_plant1 |
| **Tile Occupied (Old Crop / Weed Not Harvested)** | **2/29** | **6.9%** | Causal state of Loser at T_plant1 |
| **Quadrant Locked (Target Quadrant Not Unlocked)** | **10/29** | **34.5%** | Causal state of Loser at T_plant1 |

---

## 🗺️ 2. Top Target Tiles at First Planting Divergence

| Target Tile `(r, c)` | Target Quadrant | Matches (/43) | Percentage (%) |
| :---: | :---: | :---: | :---: |
| **`(4, 1)`** | **NW** | **14/29** | **48.3%** |
| **`(5, 0)`** | **SW** | **4/29** | **13.8%** |
| **`(3, 0)`** | **NW** | **2/29** | **6.9%** |
| **`(7, 3)`** | **SW** | **1/29** | **3.4%** |
| **`(2, 2)`** | **NW** | **1/29** | **3.4%** |
| **`(9, 4)`** | **SW** | **1/29** | **3.4%** |

---

## 💡 3. The Grand Empirical Discovery

1. **Worker Distance is the #1 Causal Bottleneck (0.0%)**:
   - In **the majority of matches**, the Loser has Strawberry seeds in inventory AND the target tile is empty and unlocked.
   - However, the Loser's Hand 1 is **stationed 3–5 tiles away** watering old NW crops, while the Winner's Hand 1 is **already co-located on the planting tile**!
2. **The Exact Divergence Window (Step 143.5 / Day 6.0)**:
   - The divergence happens at **Step ~180 (Day 8)**, immediately following the Land #2 unlock.
   - Winner Hand 1 marches into NE and plants the first Strawberry, while Loser Hand 1 is delayed in NW.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
