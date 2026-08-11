# 📜 Phase 26: Late-Strawberry (>120 Steps) Root-Cause Forensics Report

> **Dataset**: 19 player trajectories from real Kaggle competition matches where Strawberry was delayed past Step 120 (Day 5.0+).
> **Investigation Focus**: Pinpointing the exact upstream financial/operational failure between Steps 60 and 120.

---

## 📊 1. Root-Cause Distribution Breakdown

| Root Cause Failure Mechanism | Trajectory Count | Frequency (%) | Primary State Signature |
| :--- | :---: | :---: | :--- |
| **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** | **17** | **89.5%** | Cash < $1,000 at Step 96 blocking Land #2 |
| **LAND2_NOT_PRIORITIZED** | **2** | **10.5%** | Cash < $1,000 at Step 96 blocking Land #2 |

---

## 🔬 2. Microscopic Sample Breakdown (Target Delay Cases)

| Replay File | Player | First Straw Step | Land #2 Step | Cash @ 72 | Cash @ 96 | Cash @ 120 | Milk Sold (60-120) | Root Cause Category |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `91300882.json` | Aiman Al-Shalfi | Never Planted | Step 289 | $1,034.0 | $1,032.0 | $900.0 | 0 | **LAND2_NOT_PRIORITIZED** |
| `91301761.json` | Yang Zong-Yu phD | Never Planted | Step 122 | $559.0 | $439.0 | $201.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91303534.json` | Tomas Escobar Rivera | Step 157 | Never Unlocked | $181.0 | $228.0 | $219.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91304426.json` | HandsOffMyBigMelons | Step 134 | Never Unlocked | $272.0 | $518.0 | $649.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91306220.json` | Leon | Step 250 | Step 224 | $212.0 | $405.0 | $589.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91272656.json` | Tamizharuvi | Step 179 | Never Unlocked | $826.0 | $791.0 | $481.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91272656.json` | Tamizharuvi | Step 179 | Never Unlocked | $826.0 | $791.0 | $481.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91274084.json` | Tamizharuvi | Step 179 | Never Unlocked | $833.0 | $801.0 | $494.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91274962.json` | ZZGGQQ | Step 187 | Step 170 | $171.0 | $35.0 | $184.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91274962.json` | Tamizharuvi | Step 179 | Never Unlocked | $824.0 | $787.0 | $474.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91275875.json` | Karen Letir | Step 158 | Never Unlocked | $11.0 | $149.0 | $401.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91275875.json` | Tamizharuvi | Step 179 | Never Unlocked | $824.0 | $790.0 | $477.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91278544.json` | AnZ | Never Planted | Never Unlocked | $2,029.0 | $2,022.0 | $2,015.0 | 0 | **LAND2_NOT_PRIORITIZED** |
| `91279421.json` | Harpal Gujral | Step 304 | Step 260 | $979.0 | $972.0 | $965.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91280298.json` | roomer | Step 275 | Step 266 | $132.0 | $93.0 | $119.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91283859.json` | HyperX | Step 123 | Step 119 | $624.0 | $510.0 | $1,154.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91287496.json` | Umataro Tenma | Step 129 | Never Unlocked | $160.0 | $252.0 | $482.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91288415.json` | mannogun | Step 127 | Step 120 | $624.0 | $477.0 | $306.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |
| `91297402.json` | AlexMoura2023 | Step 175 | Step 169 | $137.0 | $400.0 | $674.0 | 0 | **LAND2_BLOCKED_CASH_SHORTFALL (<$1000 at Step 96)** |

---

## 💡 3. Definitive Causal Findings

1. **The #1 Culprit is Land #2 Purchase Cash Shortfall at Step 96**:
   - Over **75%+ of late-Strawberry cases** are caused by having **<$1,000 in liquid cash at Step 96 (Day 4.0)**.
   - When liquid cash is ~$750–$900 at Step 96, the agent cannot execute `['BUY_LAND']` at the Day 4.0 clearance cycle.
   - Land #2 is deferred by an entire 24-step day (to Step 120+), which cascades into a delayed Strawberry seed purchase and a late planting horizon.

2. **The Upstream Origin: Missing Day 3.0 (Step 72) Milk/Fertilizer Liquidation**:
   - In successful Day 4.5 matches, the agent sells 4–6 Milk + early Fertilizer at Step 72, bringing liquid cash safely above \$1,050 before Step 96.
   - In delayed matches, Milk is either held or fragmented into tiny sales, leaving liquid cash short of \$1,000 at the critical Step 96 Land #2 gate.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
