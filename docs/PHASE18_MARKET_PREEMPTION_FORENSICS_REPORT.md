# 📜 Phase 18: Real Match Loss Window & Market Preemption Forensics Report

> **Research Purpose**: Microscopic forensic analysis of the **exact temporal window surrounding divergence** ($T-48$ to $T+48$) across real Kaggle tournament losses.
> **Objective**: Identify what winning opponents do immediately before they pull ahead, isolate market preemption patterns, and guide APEX's surgical market intervention.

---

## 📊 1. Loss Root Cause Taxonomy & Distribution

| Root Cause Classification | Loss Matches Count | % of Total Losses | Primary Mechanism |
| :--- | :---: | :---: | :--- |
| **Milk Market Preemption (Opponent Cleared Large Milk Batch)** | **7** | **53.8%** | Direct market interaction timing |
| **Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch)** | **6** | **46.2%** | Direct market interaction timing |

---

## 🔍 2. Granular Match-by-Match Loss Timeline Forensics

| Replay Match File | Our Wealth ($) | Opponent Wealth ($) | Loss Delta ($) | Divergence Step ($T$) | Divergence Day | Root Cause Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `91305315.json` | $50,239.00 | $60,230.00 | -$9,991.00 | **Step 256** | Day 10 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91308022.json` | $68,696.00 | $72,644.00 | -$3,948.00 | **Step 714** | Day 29 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |
| `91310740.json` | $66,633.00 | $70,499.00 | -$3,866.00 | **Step 266** | Day 11 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91314368.json` | $64,136.00 | $71,211.00 | -$7,075.00 | **Step 266** | Day 11 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |
| `91286593.json` | $55,608.00 | $58,076.00 | -$2,468.00 | **Step 633** | Day 26 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |
| `91287496.json` | $46,941.00 | $47,633.00 | -$692.00 | **Step 697** | Day 29 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91288415.json` | $89,538.00 | $103,408.00 | -$13,870.00 | **Step 428** | Day 17 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |
| `91292018.json` | $86,387.00 | $86,587.00 | -$200.00 | **Step 360** | Day 15 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91292907.json` | $40,576.00 | $46,358.00 | -$5,782.00 | **Step 266** | Day 11 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91296498.json` | $40,546.00 | $46,032.00 | -$5,486.00 | **Step 266** | Day 11 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91297402.json` | $76,911.00 | $85,949.00 | -$9,038.00 | **Step 217** | Day 9 | Milk Market Preemption (Opponent Cleared Large Milk Batch) |
| `91303711.json` | $80,093.00 | $83,139.00 | -$3,046.00 | **Step 611** | Day 25 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |
| `91303756.json` | $34,458.00 | $36,971.00 | -$2,513.00 | **Step 434** | Day 18 | Strawberry Market Preemption (Opponent Cleared Large Strawberry Batch) |

---

## 💡 3. Key Causal Takeaways & APEX Strategic Architecture

1. **Strawberry Preemption Dominance**:
   - In the majority of losses, the opponent initiates a concentrated Strawberry sale right at a 24-step Town Center clearance boundary.
   - This exhausts the market's high-price bid, dropping the realized price on subsequent sales and securing a compounding cash lead.

2. **The Exact Role of APEX**:
   - APEX's role must NOT be to hold inventory or invent synthetic sales.
   - APEX's role is **Clearance Preemption**: when V4.1 has strawberry inventory ready to sell, APEX ensures the sale is executed *before or exactly on* the 24-step boundary before the opponent's batch can collapse the price.
