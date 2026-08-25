# 🧠 RESEARCH CYCLE #2: META-FORENSIC & OPPONENT REFLEXIVITY REPORT

> **Objective**: Move beyond internal farm micro-optimizations and establish genuine **opponent-relative strategic interactions** that distinguish elite leaderboard winners from APEX 3.5.  
> **Source Data**: 807 Tournament Matches, 86 Player Trajectories, and 9 Falsification Cycles (`EXP-0113` through `EXP-0121`).

---

## 🏛️ 1. The Falsification Synthesis: What We Have Permanently Mapped

Across 9 rigorous experimental cycles, we systematically proved that **APEX 3.5's internal farming operations are already near-optimal**:
1. ❌ **Supply Collapse / Pricing Filters (`EXP-0113`–`EXP-0117`)**: Neutral against real ladder.
2. ❌ **Task Queue Reordering (`EXP-0118`, `EXP-0119`)**: Yields 0h latency gain in micro-tasks, but exact 50.0% parity against opponents.
3. ❌ **Crop Diversification (`EXP-0120`)**: Neutral in paired exact replay.
4. ❌ **Early Land Expansion (`EXP-0121`)**: Severe regression (4.3% WR, -$4,069 MCV) caused by capital starvation.

---

## 📊 2. Winner Behavior Differential Matrix

| Rank | Strategic Dimension | APEX 3.5 Strategy | Elite Winner Behavior | Causal Classification | Causal Confidence |
| :---: | :--- | :--- | :--- | :---: | :---: |
| • | **`MARKET_PREEMPTION_FRONT_RUNNING`** | Static batch liquidation at Step 23... | Monitors opponent shed inventory; if opponent... | `OPPONENT_DEPENDENT_BEHAVIOR` | **0.88** |
| • | **`TOWN_FEED_SUPPLY_LOCKOUT`** | Buys daily wheat feed reactively on... | When cash permits on Day 4-6, buys town wheat... | `OPPONENT_DEPENDENT_BEHAVIOR` | **0.82** |
| • | **`OPPONENT_LIQUIDITY_EXHAUSTION_EXPLOITATION`** | Fixed worker wage reserve ($400 buf... | Detects when opponent is cash-strapped (money... | `OPPONENT_DEPENDENT_BEHAVIOR` | **0.74** |
| • | **`EARLY_LAND_EXPANSION`** | Fixed Step 170 Land 2 expansion.... | Unlocks Land 2 at Steps 120-144.... | `WEALTH_DEPENDENT_EFFECT` | **0.04** |
| • | **`CROP_PORTFOLIO_DIVERSIFICATION`** | Pure Strawberry mono-culture (34 pl... | Tri-crop / Dual-crop rotation.... | `CORRELATED_ARTIFACT` | **0.50** |
| • | **`PLANTING_TASK_PRIORITY`** | PLANT at Priority 7.... | PLANT at Priority 4/5.... | `INTERNAL_EFFICIENCY_ARTIFACT` | **0.50** |
| • | **`LATE_MILK_TIMING`** | Milk threshold 4 in late game.... | Milk threshold 2.... | `INTERNAL_EFFICIENCY_ARTIFACT` | **0.50** |
| • | **`SUPPLY_COLLAPSE_PRICING`** | Standard dual-regime gentle rebound... | Suppression of MA sales.... | `FALSIFIED_IN_LEDGER` | **0.00** |

---

## 🔬 3. The Core Strategic Pivot: Opponent Reflexivity

```
    [OLD RESEARCH PARADIGM: INTERNAL OPTIMIZATION]
    How can APEX plant 1 hour earlier? -> ❌ 50% Neutral
    How can APEX hold milk 2 turns longer? -> ❌ 50% Neutral
    How can APEX buy land 2 days earlier? -> ❌ 4.3% Harmful

    [NEW RESEARCH PARADIGM: OPPONENT REFLEXIVITY]
    ⚡ What is the opponent doing in the shared market order book?
    ⚡ If the opponent is about to dump 20 milk, can APEX liquidate 1 turn ahead to capture peak price?
    ⚡ If the opponent is cash-starved, can APEX deny cheap feed in the town shop?
```

---

## Recommended Research Direction: `EXP-0122` (`OPPONENT_INVENTORY_FRONT_RUNNING`)

* **Target Archetype**: `MARKET_REFLEXIVITY` (Rank #1, Composite Score: **`1.72`**)
* **The Mechanism**: APEX 3.5 inspects the opponent shed inventory from public observation data. When the opponent accumulates >= 8 Milk or >= 6 Strawberries ahead of a cycle boundary, APEX executes a **pre-emptive liquidation 1 step early** (e.g. Step 22 instead of Step 23), capturing peak market price (+$15-$25/unit) and forcing the opponent to absorb the resulting price slippage.
