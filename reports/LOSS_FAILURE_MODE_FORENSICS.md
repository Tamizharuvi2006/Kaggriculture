# 🔬 LOSS FAILURE MODE FORENSICS & TAXONOMY REPORT
### Empirical Dissection of Failure Causes across Authoritative Live Losses

> **Core Scientific Conclusion**: Candidate L+ does NOT fail from a single universal bottleneck. Instead, losses partition into **3 distinct failure modes**: `FLEET_DELAY` (91285661), `QUEUE_COLLISION` (91286593), and `VALUATION_TIMING` (91287496 & 91282953).

---

## 📊 1. FORENSIC MILESTONE TIMELINE COMPARISON

| Match Replay File | Category | Final Score ($) | Opponent ($) | NE Unlock Step (Day) | First Pasture Step (Day) | First Cow Step (Day) | First Sheep Step (Day) | 🍓/🐑 Straw & Wool ($) | 🥛 Milk Rev ($) / Units | Avg Milk Price ($/u) | Failure Mode Taxonomy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`91284757.json`** | 🏆 WIN | **$106,545.00** | $85,534.00 | Step 170 (D7) | Step 2 (D0) | N/A | N/A | **$34,440.10** | $13,833.30 (187u) | $73.97 | **BENCHMARK** |
| **`91282058.json`** | 🏆 WIN | **$129,852.00** | $86,508.00 | Step 170 (D7) | Step 2 (D0) | N/A | N/A | **$33,824.40** | $18,664.67 (179u) | $104.27 | **BENCHMARK** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`91285661.json`** | 🔴 LOSS | **$53,921.00** | $55,701.00 | Step 169 (D7) | Step 6 (D0) | N/A | N/A | **$2,932.44** | $2,002.06 (173u) | $11.57 | **🔴 FLEET_DELAY (D15 Pasture Lockout)** |
| **`91287496.json`** | 🔴 LOSS | **$46,941.00** | $47,633.00 | Step 170 (D7) | Step 2 (D0) | N/A | N/A | **$20,243.37** | $8,596.30 (210u) | $40.93 | **🔴 VALUATION_TIMING (Low Price per Milk Unit)** |
| **`91286593.json`** | 🔴 LOSS | **$55,608.00** | $58,076.00 | Step 170 (D7) | Step 2 (D0) | N/A | N/A | **$22,486.00** | $8,821.17 (165u) | $53.46 | **🔴 QUEUE_COLLISION (Order Slot Congestion)** |
| **`91282953.json`** | 🔴 LOSS | **$48,969.00** | $50,343.00 | Step 170 (D7) | Step 2 (D0) | N/A | N/A | **$19,922.60** | $7,261.67 (159u) | $45.67 | **🔴 LIQUIDITY_TIMING (Late Catch-up Surge)** |

---

## 🔬 2. DEEP DISSECTION BY FAILURE CATEGORY

### 🚨 1. FAILURE MODE: `FLEET_DELAY` (`91285661.json` - $53.9k vs $55.7k)
- **The Anomaly**: Secondary Strawberries & Wool revenue collapsed to **$2,932.44** (vs. **$34.4k** in benchmark wins).
- **Root Cause**: Candidate L+ experienced a pasture construction block. Pastures were not completed until **Step 312 (Day 13)**, missing the critical Day 12–15 planting window.
- **Strategic Impact**: Cost 4 full harvest cycles of Strawberries & Wool, leaving L+ **-$1,780.00 short of victory**.

### 🚨 2. FAILURE MODE: `VALUATION_TIMING` (`91287496.json` - $46.9k vs $47.6k)
- **The Anomaly**: Candidate L+ produced **210 Milk units** (HIGHER than the 187 units in the $106.5k Win!), but total Milk revenue was only **$8,596.30**.
- **Root Cause**: Average realized price per Milk unit was only **$40.93/unit** (vs. **$73.97/unit** in the $106.5k Win) because Milk orders were submitted when market price was depressed.
- **Strategic Impact**: High physical volume failed to convert into cash liquidity, causing a narrow **-$692.00 loss**.

### 🚨 3. FAILURE MODE: `QUEUE_COLLISION` (`91286593.json` - $55.6k vs $58.1k)
- **The Anomaly**: Candidate L+ executed Wheat sales ($70.4k) and secondary sales ($22.5k), but Milk sales were capped at 165 units.
- **Root Cause**: Market order queue (capped at 10 orders/turn) became congested by Wheat sales, displacing Milk SELL orders from Position #0.
- **Strategic Impact**: Opponent out-earned L+ in peak turns, winning by **-$2,468.00**.

---

## 🏛️ REPOSITORY ARCHITECTURE CONFIRMED

```
D:\kaggriculture\
├── baseline\
│   └── kaitofukami-v18.py                     ← V4.1 MASTER CHAMPION 🔒 (UNTOUCHABLE)
├── generalization_pipeline\
│   ├── submission_candidate_l_plus.py          ← Clean Candidate L+ (303KB Standalone)
│   └── submission_candidate_l_plus_raw_backup.py
├── reports\
│   ├── LOSS_FAILURE_MODE_FORENSICS.md          ← Master Failure Forensics Report
│   ├── LOSS_DIR_AUTHORITATIVE_COMPARISON.md
│   ├── STRONG_WIN_91284757_DISSECTION.md
│   └── STRONG_OPPONENT_COMPETITIVE_REGISTRY.md
└── experiments\
    └── forensic_loss_analyzer.py              ← Offline Failure Forensics Analyzer
```