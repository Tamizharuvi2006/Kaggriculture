# 📜 Phase 13: Top-Tier Production Pipeline Forensics Report

> **Research Purpose**: Deep forensic extraction comparing **V4.1 Master Baseline** vs **Top 3000+ Replays** across 71 real Kaggle matches.
> **Key Metric Focus**: Production pipeline throughput, timing cadence, and **Revenue per Land / Worker / Step** across Strawberry, Milk, Wool, Wheat, and Melon.

---

## 📊 1. Production Pipeline Master Comparison Table

| Metric / Commodity Pipeline | V4.1 Master Baseline (30 Seeds) | Top-Tier Winning Replays (3000+) | Strategic Difference / Gap |
| :--- | :---: | :---: | :--- |
| **Mean Final Wealth** | **$98,645.23** | **$90,057.15** | **+$-8,588.09 (+-8.7%)** |
| **🍓 Strawberry First Planting** | Step 107.0 (Day 4.5) | Step 115.1 (Day 4.8) | **Top tier enters Strawberry earlier** |
| **🍓 Strawberry Units Sold** | 616.0 units | 519.7 units | **+-96.3 units** |
| **🍓 Strawberry Gross Revenue** | **$91,861.67** (93.1%) | **$81,382.41** (90.4%) | **#1 Crop Revenue Driver** |
| **🍓 Strawberry Avg Sell Batch** | 7.8 units/order | 8.0 units/order | Deliberate batch liquidation |
| **🥛 Milk First Cow Purchased** | Step 1.0 (Day 0.0) | Step 1.1 (Day 0.0) | Cow unlock timing |
| **🥛 Milk Peak Herd Size** | 2.0 cows | 2.3 cows | Sustainable herd size |
| **🥛 Milk Gross Revenue** | **$69,532.90** (70.5%) | **$74,329.59** (82.5%) | **#2 Wealth Driver** |
| **🐑 Wool Gross Revenue** | **$49,908.40** (50.6%) | **$32,357.50** (35.9%) | High-margin secondary animal |
| **🌾 Wheat Gross Revenue** | **$49,488.07** (50.2%) | **$40,302.88** (44.8%) | Working capital velocity |
| **🍈 Melon Gross Revenue** | **$33,724.03** (34.2%) | **$24,997.85** (27.8%) | Late-game bulk crop |

---

## ⚡ 2. Production Efficiency Metrics

| Efficiency Dimension | V4.1 Master Baseline | Top-Tier Replays (3000+) | Efficiency Gap |
| :--- | :---: | :---: | :---: |
| **Revenue per Land Quadrant / Day** | **$1,096.06** / quad / day | **$1,000.63** / quad / day | **+$-95.42/day** |
| **Revenue per Worker / Hour (Step)** | **$34.25** / worker / step | **$31.27** / worker / step | **+$-2.98/step** |

---

## 🎯 3. 1200+ Loss Boundary Diagnosis: Question A vs Question B

> **Question A**: Are we losing because our farm production pipeline is strategically worse?
> **Question B**: Are we losing because matchmaking exposes us to stronger 2000+ opponents where small rating deltas cause asymmetric loss penalties?

### Empirical Diagnosis:
1. **Opponent Wealth in Losses**: In recorded loss replays, opponents achieved an average final wealth of **$66,825.92**, while self-wealth dropped to **$61,597.08**.
2. **Causal Bottleneck**: Losses are driven by **market preemption in the Strawberry & Milk pipelines**. When a top opponent floods the Town Center market slots or sells out animal feed, V4.1's cash flow stalls, whereas top bots maintain diversified liquidity pipelines!

---

## 🏛️ Strategic Directives & Architectural Status

- 🛡️ **V4.1 Master Champion (Ref `55249106`, 1479.8)**: **100% PROTECTED & UNTOUCHED**.
- 📦 **APEX 3.0 (Ref `55411304`, 1191.0)**: Benchmark record preserved.
- 🔒 **APEX 3.2**: Frozen locally (0 uploads executed).
- 🔬 **Next Action**: Execute counterfactual testing on the **Strawberry + Milk synchronization engine** before constructing any new candidate submission!
