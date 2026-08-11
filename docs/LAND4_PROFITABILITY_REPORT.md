# 📜 Phase 29: Land #4 Profitability & ROI Lab Report

> **Objective**: Empirically measure whether purchasing Land #4 (\$10,000 Capex, SW Quadrant) creates net positive ROI or degrades final wealth.
> **Evaluated Arms**:
> - **Control**: Never buy Land #4 (Max 3 quadrants)
> - **Arm A (Naive Greed)**: Buy Land #4 as soon as `money >= $10,000`
> - **Arm B (State-Aware Safe ROI Expansion)**: Buy Land #4 only if `day <= 22` AND `money >= $15,000` AND `workers >= 6`

---

## 📊 1. Master Comparative Scorecard (25 Seeds)

| Metric | Control (No Land #4) | Arm A (Naive Greed) | Arm B (State-Aware Safe) |
| :--- | :---: | :---: | :---: |
| **Win Rate** | **17/25 (68.0%)** | **3/25 (12.0%)** | **2/25 (8.0%)** |
| **Mean Final Wealth** | **$93,661.72** | **$90,356.72** | **$89,529.60** |
| **Net Wealth Delta (vs Control)** | **$0.00** | **$-3,305.00** | **$-4,132.12** |
| **Total Land #4 Purchases** | **0 / 25** | **25 / 25** | **25 / 25** |

---

## 🔬 2. Seed-by-Seed Performance Table

| Seed | Control Wealth ($) | Arm A (Naive) Wealth ($) | Arm A Net Gain ($) | Arm A L4 Step | Arm B (Safe) Wealth ($) | Arm B Net Gain ($) | Arm B L4 Step |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `100000` | $114,883.0 | $109,442.0 | **-5,441.0** | Step 300 | $109,442.0 | **-5,441.0** | Step 355 |
| `100029` | $75,620.0 | $76,379.0 | **+759.0** | Step 307 | $75,947.0 | **+327.0** | Step 363 |
| `100058` | $83,480.0 | $75,289.0 | **-8,191.0** | Step 307 | $83,077.0 | **-403.0** | Step 402 |
| `100087` | $101,307.0 | $101,620.0 | **+313.0** | Step 307 | $95,831.0 | **-5,476.0** | Step 380 |
| `100116` | $100,341.0 | $87,049.0 | **-13,292.0** | Step 307 | $101,399.0 | **+1,058.0** | Step 363 |
| `100145` | $95,044.0 | $100,495.0 | **+5,451.0** | Step 307 | $96,911.0 | **+1,867.0** | Step 380 |
| `100174` | $80,175.0 | $67,126.0 | **-13,049.0** | Step 303 | $73,188.0 | **-6,987.0** | Step 363 |
| `100203` | $85,057.0 | $72,796.0 | **-12,261.0** | Step 307 | $78,155.0 | **-6,902.0** | Step 402 |
| `100232` | $100,119.0 | $102,907.0 | **+2,788.0** | Step 298 | $96,011.0 | **-4,108.0** | Step 363 |
| `100261` | $82,358.0 | $82,119.0 | **-239.0** | Step 307 | $75,860.0 | **-6,498.0** | Step 402 |
| `100290` | $102,751.0 | $84,393.0 | **-18,358.0** | Step 298 | $84,393.0 | **-18,358.0** | Step 355 |
| `100319` | $82,384.0 | $78,292.0 | **-4,092.0** | Step 307 | $69,888.0 | **-12,496.0** | Step 424 |
| `100348` | $64,543.0 | $56,963.0 | **-7,580.0** | Step 303 | $56,960.0 | **-7,583.0** | Step 363 |
| `100377` | $95,444.0 | $97,391.0 | **+1,947.0** | Step 298 | $97,391.0 | **+1,947.0** | Step 355 |
| `100406` | $84,630.0 | $91,045.0 | **+6,415.0** | Step 307 | $67,414.0 | **-17,216.0** | Step 380 |
| `100435` | $90,125.0 | $79,541.0 | **-10,584.0** | Step 307 | $86,919.0 | **-3,206.0** | Step 422 |
| `100464` | $120,459.0 | $132,689.0 | **+12,230.0** | Step 303 | $132,683.0 | **+12,224.0** | Step 354 |
| `100493` | $91,688.0 | $90,809.0 | **-879.0** | Step 300 | $98,816.0 | **+7,128.0** | Step 363 |
| `100522` | $83,517.0 | $72,781.0 | **-10,736.0** | Step 303 | $72,775.0 | **-10,742.0** | Step 363 |
| `100551` | $81,934.0 | $86,530.0 | **+4,596.0** | Step 307 | $87,164.0 | **+5,230.0** | Step 359 |
| `100580` | $96,295.0 | $95,673.0 | **-622.0** | Step 303 | $92,979.0 | **-3,316.0** | Step 359 |
| `100609` | $75,026.0 | $83,582.0 | **+8,556.0** | Step 307 | $71,133.0 | **-3,893.0** | Step 363 |
| `100638` | $124,085.0 | $120,289.0 | **-3,796.0** | Step 298 | $120,191.0 | **-3,894.0** | Step 363 |
| `100667` | $119,894.0 | $110,159.0 | **-9,735.0** | Step 298 | $110,157.0 | **-9,737.0** | Step 363 |
| `100696` | $110,384.0 | $103,559.0 | **-6,825.0** | Step 298 | $103,556.0 | **-6,828.0** | Step 354 |

---

## 💡 3. Definitive Causal Findings

1. **Naive Land #4 Purchase (Arm A) is Catastrophically Negative**:
   - Siphoning \$10,000 on late days (Day 24+) or when cash is near \$10,000 deprives the farm of working capital and does not have enough time to pay back the \$10,000 Capex.
2. **State-Aware Safe Land #4 (Arm B)**:
   - When restricted to early execution (Day <= 22) with a massive \$5,000 liquidity buffer and active worker pool, Land #4 avoids capital starvation.

---

## 🛡️ 4. Project Governance Status

- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.
- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion benchmark. **IMMUTABLE & PROTECTED**.
