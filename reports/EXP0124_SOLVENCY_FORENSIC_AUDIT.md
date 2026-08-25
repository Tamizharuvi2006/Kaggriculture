# EXP-0124: SOLVENCY & CAPITAL PRESERVATION FORENSIC AUDIT

> **Hypothesis**: Land 2 expansion is economically beneficial **if and only if** a strict **$800 - $1,000 operating cash reserve** is maintained post-purchase to fully fund immediate planting, fertilizer, wages, and animal feed.  
> **Target Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Variable Family**: `Capital_Deployment`

---

## 1. Mathematical Derivation of Solvency Reserve

```
================================================================================
[POST-EXPANSION 48-HOUR MANDATORY OPERATING EXPENDITURES]
================================================================================

  • Land 2 Quadrant Purchase Cost        : $1,000.00
  • 4x New NE Strawberry Seeds ($100 ea) :   $400.00
  • 4x Tile Fertilizer ($10 ea)          :    $40.00
  • Ongoing NW Strawberry Replanting     :   $400.00
  • 3x Worker Daily Wages (2 days @ $10) :    $60.00
  • 2x Cow Wheat Feed (2 days @ $25)     :   $100.00
  ------------------------------------------------------------------------------
  • TOTAL MANDATORY OPERATING RESERVE    : $1,000.00
  • TRUE SOLVENCY THRESHOLD AT DECISION  : $2,000.00 ($1,000 Land + $1,000 Reserve)
================================================================================
```

---

## 2. Causal Forensic Disentanglement: EXP-0121 vs EXP-0124

| Metric | EXP-0121 (Falsified @ 4.3% WR) | APEX 3.5 Baseline (Step 170) | EXP-0124 (Proposed Solvency Gating) |
| :--- | :---: | :---: | :---: |
| **Expansion Trigger Cash** | **$1,100** | **~$1,950** (Step 170 accumulation) | **$1,800 - $2,000** |
| **Land 2 Purchase Cost** | -$1,000 | -$1,000 | -$1,000 |
| **Post-Purchase Liquid Cash**| **$100** | **$950** | **$800 - $1,000** |
| **48-Hour Required Reserve** | $1,000 | $1,000 | $1,000 |
| **Capital Surplus / Deficit**| **-$900 (Catastrophic Insolvency)** | **-$50 (Solvent via Day 7 flow)** | **$0 to +$200 (100% Fully Solvent)** |
| **Physical Consequence** | Missed fertilizer, stalled planting, wage default | 100% uninterrupted operations | Captures early compounding on high-cash seeds |

---

## 3. Pre-Registered Bounded Parameter Space (for PAIRED_GPU_V2)

| Candidate ID | Min Step | Cash Threshold | Post-Purchase Reserve | Strategy Description |
| :--- | :---: | :---: | :---: | :--- |
| **`CAND-124-01`** | `170` | `$1,000` | `$0` | Fixed Step 170 (`APEX 3.5 PROD` Baseline) |
| **`CAND-124-02`** | `120` | `$1,800` | `$800` | Dynamic Unlock @ Cash >= $1,800 ($800 Reserve) |
| **`CAND-124-03`** | `120` | `$2,000` | `$1,000` | Dynamic Unlock @ Cash >= $2,000 (Full $1,000 Reserve) |
| **`CAND-124-04`** | `120` | `$2,200` | `$1,200` | Conservative Unlock @ Cash >= $2,200 ($1,200 Reserve) |
| **`CAND-124-05`** | `140` | `$1,800` | `$800` | Step >= 140 + Cash >= $1,800 |
| **`CAND-124-06`** | `140` | `$2,000` | `$1,000` | Step >= 140 + Cash >= $2,000 |
