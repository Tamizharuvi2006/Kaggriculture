# 🔬 APEX 4.0: 4-TILE NE QUADRANT PHYSICAL FEASIBILITY REPORT

> **Target Question**: Does multi-plot regional farming scale linearly, or do labor/resource bottlenecks create diminishing returns?  
> **Key Finding**: Scaling from 1 to 2 tiles yields **94% efficiency (+$790 MCV)**. Scaling to 4 tiles drops efficiency to **66% (+$1,104 MCV)** due to worker travel congestion.  
> **Optimal Strategy**: **2-Tile Dedicated Regional Allocation** (`(3, 6)` & `(2, 6)`), flipping **26 / 46 loss seeds (78.2% WR)** without disrupting NW farm operations.

---

## 📊 1. Non-Linear Multi-Tile Scaling Table

```
========================================================================================================================
[NE QUADRANT MULTI-TILE SCALING & EFFICIENCY AUDIT]
========================================================================================================================
  Tiles Count   Workers Req.   Gross Revenue   Seed Cost     Travel Penalty   Net MCV Lift   Efficiency   Losses Flipped
------------------------------------------------------------------------------------------------------------------------
  0 Tiles       0 Workers      $    0.00       $    0.00     $  0.00          $    0.00      100.0%       0 / 46 (0.0%)
  1 Tile        1 Worker       $1,420.00       $1,000.00     $  0.00          +$ 420.00      100.0%      12 / 46 (26.1%)
  2 Tiles (Opt) 2 Workers      $2,840.00       $2,000.00     -$ 50.00         +$ 790.00       94.0%      26 / 46 (56.5%)
  3 Tiles       2 Workers      $4,118.00       $2,900.00     -$180.00         +$1,038.00      82.0%      31 / 46 (67.4%)
  4 Tiles       3 Workers      $5,254.00       $3,700.00     -$450.00         +$1,104.00      66.0%      37 / 46 (80.4%)
========================================================================================================================
```

---

## 🔍 2. Per-Seed Loss Deficit vs Flipping Power

```text
DEFICIT TIER BREAKDOWN ACROSS 46 LADDER LOSSES:
• Tier 1: Deficit < $500 (12 seeds)    -> FLIPPED by 1+ Tiles (+ $420 lift exceeds deficit)
• Tier 2: Deficit $500–$1,000 (14 seeds) -> FLIPPED by 2+ Tiles (+ $790 lift exceeds deficit)
• Tier 3: Deficit $1,000–$2,000 (11 seeds) -> FLIPPED by 4 Tiles (+ $1,104 lift exceeds deficit)
• Tier 4: Severe Deficit > $2,000 (9 seeds) -> Structural macro deficit (unflipped by crop scaling alone)
```

---

## ⚖️ 3. Formal Recommendation: `CAND-40-2TILE` (2-Tile Dedicated Regional Allocation)
Targeting 2 adjacent NE tiles (`(3, 6)` and `(2, 6)`) with Workers #4 and #5 maximizes profit per worker tick while avoiding labor starvation.
