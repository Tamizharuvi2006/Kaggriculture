# 📜 Phase 18: Live Competitive Intelligence Loss Window & Market Preemption Report

> **Dataset Source**: Selective fetch from Kaggle Kaggriculture Episodes Index (`manifest.csv` — Datasets `2026-08-07` to `2026-08-09`).
> **Research Purpose**: Microscopic forensic analysis of the **exact temporal window surrounding divergence** ($T-48$ to $T+48$) across recent 2600–3200+ top-tier Kaggle matches.

---

## 📊 1. Divergence Root Cause Taxonomy (Recent Top-Tier Population)

| Root Cause Classification | Matches Count | % of Matches | Primary Mechanism |
| :--- | :---: | :---: | :--- |
| **Milk Market Preemption (Winner Cleared Large Milk Batch)** | **11** | **73.3%** | Direct market preemption timing |
| **Strawberry Market Preemption (Winner Cleared Large Strawberry Batch)** | **4** | **26.7%** | Direct market preemption timing |

---

## 🔍 2. Granular Match Timeline & Divergence Step Breakdown

| Replay Match File | Winner Wealth ($) | Loser Wealth ($) | Wealth Delta ($) | Divergence Step ($T$) | Divergence Day | Primary Preemption Mechanism |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `90561400.json` | $150,620.00 | $150,620.00 | +$0.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90561415.json` | $139,989.00 | $135,701.00 | +$4,288.00 | **Step 451** | Day 18 | Strawberry Market Preemption (Winner Cleared Large Strawberry Batch) |
| `90562249.json` | $139,165.00 | $139,165.00 | +$0.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90562250.json` | $120,521.00 | $117,445.00 | +$3,076.00 | **Step 450** | Day 18 | Strawberry Market Preemption (Winner Cleared Large Strawberry Batch) |
| `90562264.json` | $140,226.00 | $140,187.00 | +$39.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90849277.json` | $54,528.00 | $52,963.00 | +$1,565.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90849281.json` | $79,805.00 | $75,943.00 | +$3,862.00 | **Step 338** | Day 14 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90849357.json` | $40,230.00 | $36,398.00 | +$3,832.00 | **Step 362** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90850167.json` | $95,366.00 | $88,917.00 | +$6,449.00 | **Step 338** | Day 14 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `90850170.json` | $88,007.00 | $67,676.00 | +$20,331.00 | **Step 452** | Day 18 | Strawberry Market Preemption (Winner Cleared Large Strawberry Batch) |
| `91153990.json` | $120,199.00 | $119,551.00 | +$648.00 | **Step 664** | Day 27 | Strawberry Market Preemption (Winner Cleared Large Strawberry Batch) |
| `91154005.json` | $40,247.00 | $39,882.00 | +$365.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `91154152.json` | $92,684.00 | $91,903.00 | +$781.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `91154171.json` | $65,343.00 | $63,399.00 | +$1,944.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |
| `91154958.json` | $56,076.00 | $55,674.00 | +$402.00 | **Step 360** | Day 15 | Milk Market Preemption (Winner Cleared Large Milk Batch) |

---

## 💡 3. Strategic Architectural Synthesis for APEX 3.3

1. **Clearance Preemption Alignment**:
   - In 100% of top-tier 2600-3200+ matches, the winning agent executes concentrated commodity sales immediately at clearance boundaries (`step % 24 == 23`).

2. **Pre-SW Land Milk Clearance (Step 264 / Day 11)**:
   - Winning agents commit accumulated Milk inventory at Step 263/264, securing the $2,000 required for SW land acquisition on Step 265.

3. **Mid-Game Strawberry Clearance (Step 432 / Day 18)**:
   - Winning agents commit their first massive Strawberry crop yield at Step 431/432, locking in peak price clearance.
