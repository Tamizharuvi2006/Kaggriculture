# 📜 Phase 15: Production Capacity & Worker Utilization Forensics Report

> **Research Purpose**: Granular deconstruction of worker time budgets, animal acquisition conditions, and production cycle latencies across **71 Top-Tier Replays** vs **30 V4.1 Master Trajectories** under 24-step parity.
> **Objective**: Identify the true causal source of top-tier productive superiority without fighting the liquidity mechanics.

---

## 📊 1. Worker Utilization & Action Taxonomy Breakdown

| Utilization Metric | Top-Tier Winning Champions (71 Replays) | V4.1 Master Baseline (30 Seeds) | Replay Defeated Opponents | Delta (Top vs V4.1) |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Final Wealth ($)** | **$90,057.15** | $89,210.37 | $60,249.50 | **+$846.78** |
| **Total Worker Turns** | 7,478.8 | 7,355.0 | 6,958.4 | +123.8 |
| **Productive Action Ratio** | **31.58%** | 33.09% | 28.37% | **-1.51%** |
| **Travel / Walking Ratio** | 54.87% | 56.02% | 54.05% | -1.15% |
| **Idle / Wasted Ratio** | **7.95%** | 5.14% | 12.56% | **+2.81%** |
| **Reinvestment Latency** | **31.00 steps** | 19.51 steps | 21.81 steps | **+11.49 steps** |

---

## 🐄 2. Animal Acquisition State Conditions

| Acquisition Event | Top-Tier Step | V4.1 Step | Top Cash Before ($) | V4.1 Cash Before ($) | Top Workers | V4.1 Workers |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cow #1 Acquisition** | Step 1.1 | Step 0.0 | $1,757.06 | $3,000.00 | 3.9 | 1.0 |
| **Cow #2 Acquisition** | Step 24.5 | Step 1.0 | $1,245.71 | $2,058.00 | 5.0 | 3.0 |
| **Cow #3 Acquisition** | Step 49.1764705882353 | N/A | $1,192.85 | N/A | N/A | N/A |

---

## 🌾 3. Productive Verb Distribution (Average Actions per Episode)

| Action Verb | Top-Tier Champions | V4.1 Master Baseline | Delta |
| :--- | :---: | :---: | :---: |
| **WATER** | 844.1 | 851.0 | -6.9 |
| **HARVEST** | 321.8 | 338.0 | -16.2 |
| **FEED** | 309.6 | 319.0 | -9.4 |
| **CARE** | 305.4 | 308.0 | -2.6 |
| **PICKUP** | 297.6 | 339.0 | -41.4 |
| **PLANT** | 124.9 | 131.0 | -6.1 |
| **FERTILIZE** | 102.3 | 107.0 | -4.7 |
| **PLACE** | 24.3 | 27.0 | -2.7 |
| **BUILD_PASTURE** | 14.2 | 14.0 | +0.2 |

---

## 🔍 4. Key Causal Takeaways

1. **Worker Utilization Discrepancy**:
   - Compares the ratio of productive actions (tilling, planting, harvesting, feeding, care) versus spatial travel steps.
   - Shows where travel routing inefficiencies drain valuable worker cycles.

2. **Cow #2 Acquisition State Frontier**:
   - Reveals the exact state envelope (Cash, Workers, Feed) under which winning agents transition from 1 cow to 2 cows.

3. **Reinvestment Velocity**:
   - Measures how immediately cash proceeds are redeployed into revenue-generating inputs (seeds, feed, labor).
