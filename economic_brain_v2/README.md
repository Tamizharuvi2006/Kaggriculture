# Economic Brain V2 — Autonomous Production System

This directory contains the complete, self-contained implementation, benchmark suite, and forensic audit tools for the **Zero-Tape Economic Brain Architecture** for Kaggriculture.

---

## 📂 File Directory

| File | Description |
| :--- | :--- |
| **`submission_adaptive_v2_economic.py`** | **Production Agent (V2)**: 100% observation-driven controller with multi-output livestock valuation, on-farm feed allocation, fertilizer liquidity pump, and dynamic land/labor sizing. Zero hardcoded tapes. |
| **`submission_adaptive_economic_v1.py`** | **Transition Candidate (V1)**: The initial clean, tape-free baseline extracted from V18. |
| **`benchmark_v2_ledger.py`** | **5-Match Financial Ledger**: Runs counterfactual simulations against 5 live tournament losses and generates a complete line-item financial ledger (Milk, Wool, Fertilizer, Wages, Feed, Land). |
| **`analyze_ricardo.py`** | **Forensic Audit Script**: Reverse-engineered 1052 Elo champion RicardoLópez's exact 720-turn match replay (`episode-104475527-replay.json`). |
| **`build_adaptive_v2_economic.py`** | **Pipeline Builder (V2)**: Automated assembly pipeline that combines the dynamic economic planner with the physical execution dispatcher. |
| **`build_adaptive_economic_v1.py`** | **Pipeline Builder (V1)**: Assembly pipeline for the V1 candidate. |
| **`trace_cand_v1.py`** | **Step-by-Step State Tracer**: Telemetry tool logging farm cash, plant counts, worker tasks, unwatered tiles, and animal counts across 2-day intervals. |
| **`inspect_prices.py`** | **Price Monitor**: Tracks commodity spot price fluctuations across town shops every 48 steps. |
| **`check_day6_hire.py`** | **Labor Diagnostic Tool**: Inspects market order generation, hiring budgets, and order capacity constraints at daily rollover hours. |
| **`full_strategy.py`** | **Strategy Config Block**: Modular configuration parameters used by the economic dispatcher. |

---

## 💡 Core Breakthroughs & Principles

### 1. The Virtuous Grain–Livestock Cycle (RicardoLópez Audit)
* **The Open-Market Feed Trap**: Our old bot bought 967 units of open-market wheat for **$40,994**, turning livestock into a massive financial loss when milk prices fell.
* **On-Farm Grain Self-Sufficiency**: Ricardo bought **187 wheat seeds ($1,870)** and grew **1,122 wheat** on-farm. Feed cost was **$1.67 per unit** rather than $45.00.
* **Net Margin**: At $1.67/feed, cows and sheep remain wildly profitable even under depressed product prices.

### 2. Multi-Output Livestock Valuation
Livestock is not evaluated solely on Milk or Wool:
$$\text{Daily Value} = \text{Product (Milk / Wool)} + \text{Fertilizer (\$40–\$50)} - \text{On-Farm Feed (\$1.67)} - \text{Labor Overhead}$$
* Animals produce 1 fertilizer every single day.
* Liquidating fertilizer into town markets generates **+$500 to +$700 daily cashflow**, which covers **100% of all worker wages**.

### 3. Sunk Capital Rule & Starvation Prevention
* In Kaggriculture, if an animal is unfed for 2 consecutive days, it dies permanently.
* Sunk capital is $400 (Cow) or $500 (Sheep). Letting an animal starve to save $45 in feed destroys 10x more capital.
* Emergency feed purchases must have Priority #1 in market orders ahead of discretionary hires.

### 4. Engine Land Physical Boundary
* Kaggriculture allows unlocking a maximum of **3 Quadrants**: `NW` (free), `NE` ($1,000), and `SW` ($2,000).
* Quadrant 4 (`SE`) is locked by engine design. Attempting to buy a 4th quadrant burns market slots. Land expansion must be hard-capped at 3 quadrants.

---

## 📊 Benchmark Results: V2 Economic Agent vs 5 Live Losses

| Match / Opponent | Recorded Live Tape | V2 Economic Agent | Cash Lift | Fertilizer Revenue | Milk + Wool Revenue | Feed Bleed Saved |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RicardoLópez** (`104475527`) | $29,724 | **$54,218** | **+$24,494 (+82.4%)** | +$5,528 | +$44,293 | **+$35,575** |
| **JZ** (`104424149`) | $64,276 | **$41,424** | $-22,852 | +$4,000 | +$18,869 | **+$31,915** |
| **ayman elamin** (`104433117`) | $75,049 | **$34,664** | $-40,385 | +$2,024 | +$11,148 | **+$31,879** |
| **Soumi Ghosh** (`104388418`) | $57,089 | **$45,594** | $-11,495 | +$5,130 | +$29,589 | **+$31,140** |
| **arao** (`104379472`) | $55,146 | **$45,053** | $-10,093 | +$5,195 | +$16,047 | **+$30,215** |

---

## 🏃 How to Run

### Run the 5-Match Financial Benchmark
```powershell
python D:\kaggriculture\economic_brain_v2\benchmark_v2_ledger.py
```

### Trace Step-by-Step Simulation
```powershell
python D:\kaggriculture\economic_brain_v2\trace_cand_v1.py
```

### Audit RicardoLópez's Replay
```powershell
python D:\kaggriculture\economic_brain_v2\analyze_ricardo.py
```
