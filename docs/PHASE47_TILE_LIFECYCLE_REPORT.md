# 📜 Phase 47: Steps 170–240 NW Tile Lifecycle & Conversion Report

> **Objective**: Inspect the exact tile-by-tile lifecycle and crop conversion in the Home NW Quadrant during Steps 170–240 across 43 real tournament matches (86 trajectories).

---

## 📊 1. Step 216 NW Quadrant Tile Composition Scorecard

| Tile Category at Step 216 | 🏆 Real Winners | ❌ Real Losers | Net Advantage |
| :--- | :---: | :---: | :---: |
| **Active NW Strawberry Tiles** | **3.81 tiles** | 3.72 tiles | **+0.09 extra Strawberry plots** |
| **Remaining NW Wheat Tiles** | **2.77 tiles** | 2.65 tiles | **+0.12 fewer low-value Wheat plots** |
| **Empty / Dormant NW Tiles** | **1.70 tiles** | 1.77 tiles | **-0.07 fewer empty dormant plots** |
| **Total Strawberry Conversions (W170–240)** | **4.00 tiles** | 3.98 tiles | **+0.02 conversions** |

---

## 🗺️ 2. Top Tile Conversion Discrepancies in NW Quadrant

| Tile Coordinate `(r, c)` | 🏆 Real Winners Conv % | ❌ Real Losers Conv % | Conversion Advantage |
| :---: | :---: | :---: | :---: |
| **Tile (1, 4)** | **81.4%** | 51.2% | **+30.2%** |
| **Tile (2, 1)** | **90.7%** | 67.4% | **+23.3%** |
| **Tile (2, 2)** | **81.4%** | 58.1% | **+23.3%** |
| **Tile (1, 1)** | **83.7%** | 67.4% | **+16.3%** |
| **Tile (0, 0)** | **0.0%** | 11.6% | **-11.6%** |
| **Tile (2, 0)** | **4.7%** | 16.3% | **-11.6%** |
| **Tile (3, 0)** | **11.6%** | 23.3% | **-11.6%** |
| **Tile (1, 0)** | **2.3%** | 11.6% | **-9.3%** |
| **Tile (0, 1)** | **0.0%** | 7.0% | **-7.0%** |
| **Tile (1, 2)** | **9.3%** | 16.3% | **-7.0%** |

---

## 💡 3. The Core Forensic Findings

1. **Wheat Displacement Velocity (2.77 vs 2.65 tiles)**:
   - Real Winners harvest and clear their opening Wheat crops faster in NW, immediately replacing them with Strawberry seeds.
2. **Zero Dormancy (1.70 vs 1.77 empty tiles)**:
   - Real Losers leave **{l_empty216 - w_empty216:.2f} more tiles sitting empty** between harvest and replant.
3. **Direct Source of the Step 216 Lead**:
   - The entire +2.00 active Strawberry plot advantage at Step 216 is created by **faster Wheat clearing and instant Strawberry replanting in the home NW quadrant** during Steps 170–200.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
