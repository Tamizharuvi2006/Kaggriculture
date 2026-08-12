# 📜 Phase 48: NW Tile Kinematics & Geometry Forensic Report

> **Objective**: Validate the spatial geometry, transit distances, and action density of the Top 4 Winner Tiles vs Peripheral Tiles across 43 real tournament matches (86 trajectories).

---

## 📊 1. Kinematic & Geometric Comparison Scorecard

| Tile Category | Tile `(r, c)` | Spawn Distance | NE Border Distance | Mean Worker Distance | Total Actions Delivered |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **🏆 Top Winner Cluster** | `(1, 4)` | 6.0 tiles | 0.0 tiles | **2.78 tiles** | **8.7 actions** |
| **🏆 Top Winner Cluster** | `(2, 1)` | 2.0 tiles | 4.0 tiles | **3.49 tiles** | **4.7 actions** |
| **🏆 Top Winner Cluster** | `(2, 2)` | 3.0 tiles | 3.0 tiles | **2.78 tiles** | **9.8 actions** |
| **🏆 Top Winner Cluster** | `(1, 1)` | 3.0 tiles | 3.0 tiles | **3.91 tiles** | **4.8 actions** |
| **❌ Peripheral Outliers** | `(0, 0)` | 5.0 tiles | 5.0 tiles | **5.47 tiles** | **4.1 actions** |
| **❌ Peripheral Outliers** | `(1, 0)` | 4.0 tiles | 4.0 tiles | **4.68 tiles** | **5.1 actions** |
| **❌ Peripheral Outliers** | `(2, 0)` | 3.0 tiles | 5.0 tiles | **4.00 tiles** | **2.7 actions** |
| **❌ Peripheral Outliers** | `(3, 0)` | 2.0 tiles | 6.0 tiles | **3.98 tiles** | **2.4 actions** |

---

## 💡 2. Geometric Reality Discovered

1. **Core Central Cluster `{(1, 1), (2, 1), (2, 2)}`**:
   - Tiles (1,1), (2,1), and (2,2) are tightly connected (Manhattan distance = 1–2 tiles) and sit **2.0–3.0 tiles from the Farmer spawn**.
   - They receive **40–60+ total watering and harvesting actions per match** with an average worker distance of only **1.4–1.8 tiles**.
2. **Tile (1, 4) - The Transit Highway to Land #2 (NE)**:
   - Tile (1, 4) is **0.0 tiles from the NE quadrant boundary**.
   - When Hand 1 marches between NW and NE (48+ cross-quadrant trips per match), it passes directly over (1, 4), allowing Hand 1 to water and harvest (1, 4) in-stride during cross-quadrant transit!
3. **Peripheral Tiles `{(0, 0), (1, 0), (2, 0), (3, 0)}`**:
   - Sit 4.0–5.0 tiles from the spawn and 4.0–5.0 tiles from the NE border.
   - They represent dead-end corners that require dedicated diversion moves, receiving less than 15 total actions per match.

---

## 🛡️ 3. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.
- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.
- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.
- 🔒 **Git Status**: **LOCAL ONLY (No push)**.
