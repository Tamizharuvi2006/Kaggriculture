# 🏛️ KAGGRICULTURE CURRENT STATE & RESEARCH SNAPSHOT

**Document Updated**: August 10, 2026  
**Primary Source**: Kaggle Replay Datasets, Live Ladder Forensics, Notebook Analysis (`what-actually-wins-on-the-kaggriculture-ladder.ipynb`).

---

## 📊 1. LIVE LADDER METRICS & EMPIRICAL EVIDENCE

* **Daily Score Escalation (Source: Kaggle Manifest Datasets, 2026-08-07)**:
  - July 31: Top Avg Score **1,427.0** | Median **1,175.3**
  - Aug 01: Top Avg Score **1,580.5** | Median **1,348.2**
  - Aug 02: Top Avg Score **2,627.2** | Median **2,319.2**
  - Aug 03: Top Avg Score **2,960.1** | Median **2,730.4**
  - Aug 04: Top Avg Score **2,996.3** | Median **2,767.1**
  - Aug 05: Top Avg Score **3,022.8** | Median **2,838.6**
  - Aug 06: Top Avg Score **3,081.3** | Median **2,973.4**
  - Aug 07: Top Avg Score **3,133.0** | Median **3,029.0**
  - *Confidence*: HIGH | *Sample Size*: 8 Daily Manifest Datasets.

* **Winner vs. Loser Activity Ratio (Source: 300 Replay Sample, 2026-08-07)**:
  - **Plant**: Winners 167.4 vs. Losers 162.4 (Ratio: 1.0x)
  - **Sell**: Winners 201.2 vs. Losers 235.8 (Ratio: 0.8x)
  - **Hire**: Winners 264.1 vs. Losers 266.8 (Ratio: 1.0x)
  - **Harvest**: Winners 334.3 vs. Losers 334.3 (Ratio: 1.0x)
  - **Fertilizer**: Winners 227.7 vs. Losers 231.0 (Ratio: 1.0x)
  - **Animals / Land**: 8.1 / 2.0 (Identical)
  - *Confidence*: MEDIUM-HIGH | *Sample Size*: 278 Decisive Games / 71 Agents.
  - *Core Finding*: Winners do NOT win by raw action volume. They win by **behavioral execution efficiency**.

* **Primary Crop Win Rates (Source: 2026-08-07 Replay Sample)**:
  - **STRAWBERRY Primary**: Win Rate: **56%** | *Confidence*: LOW | *Sample Size*: n = 9.
  - **WHEAT Primary**: Win Rate: **50%** | *Confidence*: HIGH | *Sample Size*: n = 547.
  - *Core Finding*: Do NOT treat Strawberry as a permanent hardcoded rule. Treat crop profitability dynamically.

* **Median Victory Margin**: **$2,688.00** ($111,063.00 winners vs $108,375.00 losers). Matches are decided at the margin!

---

## 🎯 2. KNOWN META STRATEGIES & KAGGLE SIGNALS

1. **Melon Rush**: High early-game ROI crop strategy identified in Kaggle community analysis.
2. **Headstart**: Fast early expansion / high cash-flow opening.
3. **Pasture Engine (Strawberries + Wool)**: Continuous multi-harvest production engine.

---

## ⚙️ 3. AGENT ENVIRONMENT CONSTRAINTS

* **Execution Time Limit**: Must execute `agent(obs)` strictly within per-turn timeout (< 100ms).
* **Environment**: `kaggriculture` (720 steps / 30 days, 24 steps/day).
* **Self-Contained Execution**: No external cloud network or multi-file import at runtime on Kaggle. Monolithic `.py` artifact required.

---

## 🏛️ 4. REPOSITORY BENCHMARK HIERARCHY

* **Clean Candidate**: **1254.1 Public Score** (🥇 Peak Leaderboard Candidate)
* **Candidate L+ 4.1**: **1108.6 Public Score** (🥈 Frozen Baseline Champion 🔒)
* **L+ APEX 2.0**: Autonomous In-Game Adaptive Discovery Engine ([`D:\kagriulture\Kaggriculture\apex`](file:///D:/kagriulture/Kaggriculture/apex))
