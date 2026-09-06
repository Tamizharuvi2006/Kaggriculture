# KAGGRICULTURE MASTER RESEARCH SYNTHESIS
**Consolidated Knowledge Base & Meta-Analysis of 375+ Research Reports, 300+ Experiments, and Live Telemetry**  
**Repository State:** Frozen Production Baseline RC2 (`submission.py`, SHA256: `FC1217EC...`, Kaggle Ref `55979565`)  
**Evaluation Harness:** Official Kaggriculture 5-Seed Gauntlet + 5 Live Low-Floor Seed Diagnostic Suite  

---

## 1. Executive Understanding

Across 300+ controlled experiments, multi-generation architectural rewrites, and 29 competitive live ladder matches, Kaggriculture game dynamics have converged on five fundamental truths:

1. **Production Parity vs. Realization Dominance**: In competitive matches, elite bots and our agent achieve near-identical physical capacity by Day 16: 3 unlocked quadrants (`["NW", "NE", "SW"]`), 11–13 workers, 12–14 productive animals, and 35–40 active crop tiles. The decisive separator between a $40k loss and a $100k+ win is **realized market price capture**, driven by commodity elasticity and clearance timing in the shared town order book.
2. **The Asymmetric Failure of Passive Preservation**: Unilateral market preservation, batch capping, and waiting for peak prices fail deterministically against active opponents (`EXP-0114`, `Phase 80`, `Step 5B Milk Counterfactual`). When an agent holds back sales to protect prices, the opponent exploits the window, liquidates into the high price, depresses the market, and starves our agent of operating cash.
3. **The Labor-Capacity Fragility Boundary**: Agricultural compounding is unforgiving. Under-allocating labor (e.g., `RC3-D` hiring 0 workers on Day 29) destroys tens of thousands of dollars in unharvested crops to save negligible wages ($143). Over-allocating short-cycle crops (e.g., `RC3-A` planting 60 3-day Carrots) congests workers in non-stop replanting/tilling, causing labor starvation on high-margin strawberries and livestock.
4. **Shed Capacity & Inventory Destruction**: The engine strictly enforces `shedCapacity = 100`. At the end of every day, any harvest carried by workers that cannot fit into the remaining shed room is **permanently discarded into the void** (`_drop_inventories_to_shed`). Failure to flush shed inventory every turn turns physical labor into zero-value evaporation.
5. **The Fragile Floor vs. High Ceiling**: RC2 is currently a high-ceiling ($101,119 peak, $81,237 win average), unstable-floor agent ($29,725 worst floor, $66,605 loss average). The primary cause of the low-floor collapse is not terminal realization or crop ranking; it is an **early liquidity canyon around Day 8** ($509 treasury cushion) compounded by the **Day 22–24 Melon price crash ($250 $\to$ $1)** and adverse opponent market flooding.

---

## 2. Chronological Timeline of Strategy Generations

```
V4.1 / Kaitofukami-V18 (Live Champion, TrueSkill 1714.4)
  │  15-melon opening, 8-cow pasture ceiling, closed-loop task execution.
  │  Weakness: Day 8 cash drops to $15.07; unranked market orders preempted in shared queue.
  ▼
Candidate L+ (10-Melon Opening + Position #0 Milk Preemption)
  │  Kaggle score: 1254.1 (Competition champion).
  │  Fixed early liquidity ($724 Day 8 cash); preempts milk sale at P0 when milk >= $230.
  ▼
V5 Modular Intent System (Phase 1–3b)
  │  Decoupled Intent Planner, Market Forecaster, Deployment Manager.
  │  Outcome: PERMANENTLY REJECTED (0/40 wins, 0.0% WR vs V4.1; banked $0–$3.9k).
  ▼
V8.3 Static Strategy (Caps at 12 cows, static crops)
  │  Synthetic benchmark: claimed $124k.
  │  Live Kaggle upload (55328057): COLLAPSED TO 816.8 RATING. Rolled back immediately.
  ▼
APEX 3.0 / 3.3 / 3.5 (Fixed-Schedule Hybrid Planner)
  │  APEX 3.0 (1116.5 Elo), APEX 3.3 (1024.9 Elo), APEX 3.5 (1650–1700 benchmark Elo).
  │  Introduced bounded liquidity floor, staged land unlocks (NE Day 5, SW Day 10).
  ▼
APEX 4.0 / 4.1 ML Pipeline (PPO & Opponent Classifier)
  │  APEX 4.1 original: INVALIDATED (synthetic randn observations, fabricated metrics).
  │  Rebuilt Step 5B PPO: local 500-ep pilot flat reward; Kaggle score 1018.7 (-235 pts vs L+).
  │  Frozen as research-only candidate.
  ▼
Modern V18 Cleanup → RC1 Baseline
  │  Stripped all legacy hardcoded August schedules and static heuristics.
  │  Established pure observation-driven closed-loop execution.
  ▼
RC2 Terminal Horizon (Current Live Champion, Ref 55979565)
  │  Dynamic MR/TD Economic Brain + Terminal Horizon LTV + Multi-Output Livestock ROI ($48 fert).
  │  Dedicated on-farm feed wheat plots + EV/Turn physical task dispatcher.
  │  Official 5-Seed Gauntlet: $253,054 ($50,611 avg).
  │  Live Kaggle Record: 16W - 13L (55.2% WR), Peak $101,119.
  ▼
Laboratory RC3 Iterations (RC2 Remains 100% Frozen):
  ├── RC3 Attempt 1: Slow-crop amortization filter (max_yield=4 bug) → $186,260 (REJECTED)
  ├── RC2.1: Narrow tomato planting restriction (Day 12) → $251,034 (REJECTED)
  ├── RC3-A: Market-saturation marginal portfolio → $209,810 (REJECTED: Carrot labor congestion)
  ├── RC3-D: Terminal labor shutdown (hires=0 Day 29) → $191,230 (REJECTED: Unharvested crop rot)
  └── RC3-E: Terminal realization without labor reduction → $252,538 (NEUTRAL to RC2)
```

---

## 3. Complete Experiment & Hypothesis Map

| Experiment / Phase ID | Target Hypothesis | Evaluation Mode | Gate Result | Final Classification |
| :--- | :--- | :--- | :--- | :--- |
| **`EXP-0113`** | Collapse Exit Timing avoids market dumps | Paired Gate 1 (92 seeds) | 50.0% WR, +$0 MCV | `[FALSIFIED]` |
| **`EXP-0114`** | Moving-average sell suppression prevents crashes | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED]` |
| **`EXP-0115`** | Seed buy deferral preserves working capital | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED]` |
| **`EXP-0116`** | Milk/wool holding until price recovery lifts MCV | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED]` |
| **`EXP-0117`** | $500 static safe cash buffer protects liquidity | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED]` |
| **`EXP-0118`** | Late milk timing (T2) captures peak price wave | Paired Gate 1 | 50.0% WR, -$2 MCV | `[FALSIFIED]` |
| **`EXP-0119`** | Plant priority (p4 over pasture) speeds compounding | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED / NEUTRAL]` |
| **`EXP-0120`** | Tri-crop portfolio diversification stabilizes revenue | Paired Gate 1 | 50.0% WR, +$0 MCV | `[FALSIFIED / NEUTRAL]` |
| **`EXP-0121`** | Unconditional early Land #2 expansion accelerates compounding | Paired Gate 1 | 4.3% WR, -$4,069 MCV | `[FALSIFIED - HARMFUL]` |
| **`EXP-0122`** | Front-running opponent private shed inventory avoids crashes | Architectural Audit | Unobservable in Engine | `[INVALID MECHANISM]` |
| **`EXP-0123`** | Depleting town wheat pool starves opponent livestock | Market Pool Audit | Town pool = 10k units | `[INVALID MECHANISM]` |
| **`EXP-0124`** | Solvency-gated Land #2 expansion gives durable edge | Paired Gate 1 | 50.0% WR, -$94 MCV | `[INCONCLUSIVE / NEUTRAL]` |
| **`Phase 80`** | Batch capping (max 4u Straw / 8u Milk) preserves price wave | 50 Unseen Seeds | 28.0% WR, -$540 MCV | `[FALSIFIED - HARMFUL]` |
| **`Step 5B Milk`**| Holding milk until $175+ recovers low-MCV tail | 32 Frozen Traces | -$17,275 MCV (0/5 pos) | `[FALSIFIED - HARMFUL]` |
| **`Land #4`** | Expanding to 4 quadrants increases late-game production | 25-Seed Control | $48k vs $72k for 3-land | `[FALSIFIED - HARMFUL]` |
| **`RC3 Att. 1`**| Treating `max_yield=4` as lifetime crop cap | Official 5-Seed Gauntlet| $186,260 vs $253k RC2 | `[FALSIFIED - BUG]` |
| **`RC2.1`** | Banning Tomato planting after Day 12 | Official 5-Seed Gauntlet| $251,034 vs $253k RC2 | `[FALSIFIED / NEUTRAL]` |
| **`RC3-A`** | Marginal saturation-aware portfolio allocation | Official 5-Seed Gauntlet| $209,810 vs $253k RC2 | `[FALSIFIED - LABOR]` |
| **`RC3-D`** | Shutting down Day 29 labor (hires=0) saves wages | Official 5-Seed Gauntlet| $191,230 vs $253k RC2 | `[FALSIFIED - ROT]` |
| **`RC3-E`** | Terminal realization without labor reduction | Official 5-Seed Gauntlet| $252,538 vs $253k RC2 | `[INCONCLUSIVE / NEUTRAL]`|

---

## 4. Validated Findings

1. `[VALIDATED]` **10-Melon Opening Liquidity**: Reducing opening melons from 15 to 9–10 increases Day 8 treasury from $15.07 to $509–$724, preventing early cow stall and improving win rates against passive bots.
2. `[VALIDATED]` **Shared-Market Order Preemption**: When spot milk price is high ($\ge \$230$), sorting `SELL MILK` into Position #0 in the turn's market queue guarantees execution before opponent transactions depress the price.
3. `[VALIDATED]` **Dedicated On-Farm Feed Wheat**: Sizing wheat plots to cover 100% of animal feed at on-farm cost ($1.67/unit seed cost) completely insulates the farm from inflated market wheat ($25–$50/unit) and eliminates starvation.
4. `[VALIDATED]` **Multi-Output Livestock Valuation**: Livestock profitability must include product revenue (Milk/Wool) plus Animal Care bonus (+1 unit) plus Fertilizer ($40–$55/unit liquid cash) minus Feed ($1.67) minus Worker Wages ($12/day). Under this model, Cows amortize in 4–5 days.
5. `[VALIDATED]` **3-Quadrant Plateau**: Unlocking 3 quadrants (`NW`, `NE`, `SW`) represents the optimal surface area for 11–13 workers. Expanding to Land #4 reduces final wealth by -$24,000 due to walking distance friction and capital drain.
6. `[VALIDATED]` **Terminal Labor Mandatory**: Maintaining full labor (11 workers) on Day 29 is mandatory. Every worker hired brings in $1,500+ of final harvests against a $55 marginal wage.

---

## 5. Falsified Findings

1. `[FALSIFIED]` **Unilateral Market Preservation / Batch Capping**: Throttling sales to "protect market price" is fatal in a 2-player game (`Phase 80`: 28% WR). The opponent sells into the preserved price, captures the town cash, and our agent is left holding perishable value.
2. `[FALSIFIED]` **Delayed Milk Selling / Price Waiting**: Holding milk until price exceeds $175 caused a -$17,275 MCV collapse across all audited traces. Delayed cash realization starves upstream farm operations.
3. `[FALSIFIED]` **Unconditional Early Land 2**: Rushing Land 2 on Days 4–5 without a solvency cushion caused a 4.3% win rate and -$4,069 MCV loss due to capital starvation (`EXP-0121`).
4. `[FALSIFIED]` **Town Wheat Denial**: The town market wheat pool has 10,000 units. Attempting to buy out town wheat to starve opponent animals requires $250,000 capital and is physically impossible (`EXP-0123`).
5. `[FALSIFIED]` **Solo GPU Screening Predictive Power**: Solo evaluations without shared order-book contention produced 60%+ win rates that collapsed to exactly 50.0% under official paired seat-swapped gates (`EXP-0113`–`EXP-0120`).
6. `[FALSIFIED]` **Strawberry `max_yield` Lifetime Cap**: In `kaggriculture.py`, `max_yield = 4` is the tile holding threshold before harvest, not a lifetime plant cap. Ongoing crops yield 4 units every 2 days indefinitely.

---

## 6. Inconclusive Findings

1. `[INCONCLUSIVE]` **Solvency-Gated Land 2 Expansion**: Gating Land 2 expansion by a $600–$800 cash reserve prevented catastrophes but produced exactly 50.0% win rate and -$94 MCV delta vs baseline (`EXP-0124`).
2. `[INCONCLUSIVE]` **Opponent Style Mixture Classifier**: Switching strategy presets (Wheat Rush, Cow Rush, Premium Crop) based on early opponent scouting produced positive offline counterfactuals but failed to create meaningful separation in live PPO testing.
3. `[INCONCLUSIVE]` **Terminal Realization Cutoff (RC3-E)**: Cutting off seed/land purchases on Day 27 and phasing wheat buffer to 0 scored $252,538 vs RC2's $253,054 (-$516), showing mechanical safety but no statistically significant lift.

---

## 7. Engine Mechanics Reference Table

| Engine Subsystem | Ground Truth Parameter / Rule | Strategic Consequence | Classification |
| :--- | :--- | :--- | :--- |
| **Market Clearing Function** | $P(I) = \text{round}\left(P_{\text{base}} \pm \frac{\text{target} \cdot P_{\text{base}}}{f(T)} \cdot f(|I - I_0|)\right)$ | Asymmetric, commodity-specific price curves. | `[ENGINE FACT]` |
| **Base Inventory ($I_0$)** | $I_0 = 10,000$ for all commodities | Market begins balanced; deviations drive price. | `[ENGINE FACT]` |
| **Price Floor** | $P_{\text{min}} = 1$ coin | Prices can collapse 99% but never reach 0. | `[ENGINE FACT]` |
| **Shed Capacity** | Strictly 100 units (`shedCapacity = 100`) | Overflow beyond 100 is deleted at end-of-day. | `[ENGINE FACT]` |
| **Order Queue Processing** | Interleaved slot-by-slot lockstep (Slot 0 P0/P1, Slot 1...) | Position in the turn's market list determines execution. | `[ENGINE FACT]` |
| **Market Orders per Turn** | Max 10 orders per player per turn (`maxMarketOrders = 10`)| Order slots are scarce; must prioritize high-value sales. | `[ENGINE FACT]` |
| **Town Demand Cadence** | 1 unit/product/day (Town Center) + 6 shop ticks/day | Town shops naturally drain market inventory. | `[ENGINE FACT]` |
| **Worker Spawn & Wages** | Spawns at shed; daily wages follow Fibonacci sequence | Wages escalate: $1, 1, 2, 3, 5, 8, 13, 21, 34, 55$. | `[ENGINE FACT]` |
| **Worker Inventory Drop** | Drops to shed at end of day up to capacity | Excess carried inventory is discarded if shed full. | `[ENGINE FACT]` |
| **Ongoing Crop Regrowth** | First harvest at spec day; +4 units every 2 days if watered | Multi-harvest crops compound continuously. | `[ENGINE FACT]` |
| **Livestock Care Bonus** | `CARE` action adds +1 unit to next scheduled harvest | Caring cows yields 2 milk every 2 days (+100% ROI). | `[ENGINE FACT]` |
| **Animal Starvation** | 2 consecutive unfed days permanently deletes animal | Missing feeds on Day 8 destroys $400–$500 sunk capital. | `[ENGINE FACT]` |
| **Observability Boundary** | Opponent private shed, seeds, and backpacks are HIDDEN | Can only observe public board, prices, and market pool. | `[ENGINE FACT]` |

---

## 8. Market Economics & Commodity Elasticity Curves

From `kaggriculture.py` (lines 41–75), each commodity has radically different sensitivity to inventory dumps:

```text
Commodity   | Base Price | Capacity (T) | Above Curve | Price Drop per 100 Units Above I0
------------|------------|--------------|-------------|----------------------------------
STRAWBERRY  |    $120    |     100      |   Linear    | -$192.00 (Collapses to $1 floor!)
MELON       |    $250    |     300      |  Quadratic  | -$100.00 (Steep quadratic plunge)
MILK        |    $160    |     200      |  Quadratic  | -$144.00 (Steep quadratic plunge)
TOMATO      |     $60    |     200      | Square Root | -$25.46  (Damped square root)
CARROT      |     $35    |     450      | Square Root | -$11.55  (Damped square root)
WHEAT       |     $25    |     400      | Logarithmic | -$1.73   (Highly resilient log)
WOOL        |    $200    |     200      | Square Root | -$84.85  (Moderate decay)
FERTILIZER  |     $40    |     400      | Square Root | -$12.00  (Very stable)
```

### Strategic Takeaways:
1. **Strawberry is Hyper-Fragile**: Dumping just 65 strawberries above $I_0$ collapses its price from $120 to $1. It is impossible to sell large volumes of Strawberry without crashing the market unless town shops actively consume them.
2. **Wheat is Indestructible**: Wheat has logarithmic damping (`log1p`). You can sell 500 units of wheat and the price only drops by $3–$4.
3. **The Melon Trap**: Melon has a quadratic penalty (`sq`, 3.60). When both players harvest opening melons on Day 22–24, Melon price crashes to $1–$7 across 100% of audited seeds.

---

## 9. Labor Economics & Routing Mechanics

1. **Wages are Cheap Relative to Crop Value**:
   * Hiring 11 workers costs $\sum_{i=1}^{11} \text{Fib}(i) = 1+1+2+3+5+8+13+21+34+55+89 = \mathbf{\$232/day}$.
   * 11 workers generate 264 physical actions per day.
   * A single Strawberry harvest of 4 units at $150/unit is worth **$600**. One single harvest pays for more than 2 full days of entire farm wages!
2. **Walking Distance is the Hidden Tax**:
   * Traveling 1 tile costs 1 worker turn.
   * In Land #4 (SE quadrant), workers must travel Manhattan distance $12–16$ round trip ($24–32$ turns) just to access the shed. This travel overhead explains why Land #4 produces negative ROI.
3. **The Short-Cycle Replanting Bottleneck**:
   * Carrots mature in 3 days. A 60-tile Carrot farm requires: 60 harvests + 60 tilling/weeding + 60 plantings + 180 waterings = **360 worker actions every 3 days** (120 actions/day).
   * 11 workers produce 264 actions/day. Devoting 45% of all daily labor exclusively to Carrots leaves insufficient capacity to water Strawberries or feed animals.

---

## 10. Livestock Economics & Feed Safeguards

1. **The Compounding Engine**:
   * Cow cost: $400. Daily production (with Care): 1 Milk/day (2 milk every 2 days).
   * Milk spot price: $160–$299. Daily milk value: $160–$299.
   * Daily Fertilizer value: 1 unit every 2 days = $20–$25/day.
   * Feed cost: 1 wheat = $1.67 (on-farm). Labor: 1 care + 1 milk = $24 opportunity cost.
   * Net Daily Cashflow per Cow: $\mathbf{+\$150 \text{ to } +\$290/day}$!
   * Payback period: **1.5 to 2.5 days**.
2. **The Starvation Asymmetry**:
   * Sunk capital in 8 cows + 4 sheep = **$5,200**.
   * If an animal goes unfed for 2 consecutive days, the engine permanently deletes it.
   * A single missed feeding that deletes 2 cows destroys **$800 capital + $400/day ongoing revenue**.
   * Therefore, the feed buffer is an existential priority (Priority 0).

---

## 11. Terminal-Game Economics (Days 27–29)

1. **Final Objective is Bank Money**:
   * Unsold inventory in shed, worker backpacks, or crop tiles has **$0 value** when Turn 720 concludes.
   * Sunk capital in land, pastures, and animals has **$0 salvage value**.
2. **Capital Expenditure Cutoff**:
   * Day 22+: Stop buying Animals (payback period $\ge 3$ days exceeds remaining life).
   * Day 25+: Stop buying Land (cannot recoup $2,000 cost in 4 days).
   * Day 26+: Stop buying Strawberry/Melon seeds (first harvest takes 10–12 days).
   * Day 27+: Stop buying Tomato seeds (takes 8 days).
   * Day 28+: Stop buying Carrot/Wheat seeds (takes 2–3 days).
3. **The Day 29 Labor Swarm**:
   * Day 29 must retain the full 11-worker workforce.
   * On Day 29, workers execute **zero tilling, zero seed planting, and zero watering of non-ripe crops**.
   * 100% of Day 29 labor is concentrated on: **HARVEST all ripe tiles $\to$ WALK TO SHED $\to$ DROP INVENTORY**.

---

## 12. Live Ladder Telemetry & Empirical Distribution

From our audit of all 29 competitive matches played by RC2 (`55979565`):

```text
==================================================================================
                 RC2 COMPETITIVE LADDER PERFORMANCE SUMMARY
==================================================================================
Total Matches Played:       29
Record:                     16 WINS - 13 LOSSES (55.2% Win Rate)
Current TrueSkill Rating:   635.5 Elo
Mean Score (All Matches):   $74,678
Median Score:               $77,168
Peak Score:                 $101,119 (Episode 105120317)
Runner-Up Peak:             $97,714   (Episode 105122067)
Worst Floor Score:          $29,725   (Episode 105112452)
Average Winning Margin:     +$27,485
Average Loss Margin:        -$24,726
==================================================================================
```

### Score Distribution Histogram:
* **$90k–$101k**: 7 matches (24.1%) — High-yield monetization regime.
* **$75k–$89k**: 11 matches (37.9%) — Standard competitive regime.
* **$55k–$74k**: 7 matches (24.1%) — Constrained/shared market regime.
* **<$50k (Low Floor)**: 4 matches (13.8%) — **Catastrophic failure regime**.

---

## 13. RC2 Strengths

1. **High Ceiling ($101k)**: Out-compounds standard bots through early Cow/Sheep scaling and 3-quadrant Strawberry coverage.
2. **On-Farm Feed Immunity**: Dedicates 4–8 plots of wheat directly to feed, insulating the farm from town wheat spikes.
3. **EV/Turn Physical Dispatcher**: Observation-driven assignment with friction tie-breakers prevents worker wandering.
4. **Resilient against Passive Opponents**: Achieves 80%+ win rate against sub-600 Elo bots.

---

## 14. RC2 Weaknesses

1. **Day 8 Treasury Canyon**: Cash drops to $509 across 100% of seeds, leaving zero margin for error if feed or wages spike.
2. **Melon Crash Exposure**: Plants 9 opening Melons that crash to $1 on Day 22–24, yielding negligible revenue from 9 prime NW plots.
3. **Strawberry Monoculture Vulnerability**: Concentrates 85% of land into Strawberry. If the opponent also produces strawberries, town price collapses to $16–$60, cutting total farm revenue in half.
4. **Day 29 Labor Dropdown Bug**: In `submission_rc2_terminal_horizon.py` line 977, `_hire_target` returned 6 on Day 29 instead of 11, reducing harvest capacity on the final day.

---

## 15. Known Failure Regimes

1. **The Contested Commodity Glut**: When both players plant Strawberry or Melon, the shared inventory exceeds $I_0 + T$, crashing spot price to $1. Bots with diversified livestock survive; pure strawberry bots collapse.
2. **The Day 8 Squeeze**: An aggressive opponent buys wheat early, raising market wheat to $40+. RC2 has $509 in bank cash and cannot afford emergency grain, causing animal starvation.
3. **Shed Overflow Evaporation**: Workers harvest 30+ units during late turns while shed is near 100 capacity. At end-of-day, un-dropped inventory is discarded.

---

## 16. Current Production Baseline

* **File**: [`D:/kaggriculture/submission.py`](file:///D:/kaggriculture/submission.py)
* **Status**: **FROZEN PRODUCTION BASELINE (`RC2 Terminal Horizon`)**.
* **Integrity Guarantee**: Byte-identical to submitted candidate `55979565`. Zero live modifications permitted.

---

## 17. Current Laboratory Candidates

* **`submission_rc2_terminal_horizon.py`**: Local copy of frozen baseline ($253,054 benchmark).
* **`submission_rc3_laboratory.py` (RC3-A)**: Marginal allocator ($209,810; REJECTED).
* **`submission_rc3d_laboratory.py` (RC3-D)**: Terminal labor shutdown ($191,230; REJECTED).
* **`submission_rc3e_laboratory.py` (RC3-E)**: Terminal realization without labor reduction ($252,538; NEUTRAL).

---

## 18. Research Mistakes & Benchmark Traps

1. **The Solo-Screening Mirage**: Testing a bot in single-player or exogenous-price mode generates high scores that vanish in 2-player paired evaluations (`EXP-0113`–`0120`).
2. **The Open-Loop Replay Fallacy**: Evaluating a candidate against a fixed recorded action tape from an old match does not test whether the policy can handle an adaptive opponent.
3. **The Unilateral Price Defense Trap**: Believing you can "save" market prices by holding goods. The opponent simply sells into your preserved price.
4. **Over-Diversification Congestion**: Shifting into short-cycle crops (Carrots) overwhelms the physical worker bandwidth.
5. **The Wage-Saving Penny-Wise Fallacy**: Cutting workers on Day 29 saves $143 in wages but loses $18,000 in unharvested crops.

---

## 19. What We Must NEVER Repeat

1. **NEVER implement Land #4** (proven negative across multiple independent audits).
2. **NEVER reduce labor on Day 29** (harvest swarm is mandatory).
3. **NEVER hold milk or strawberries waiting for a target price** (causes cash starvation and -$17k collapse).
4. **NEVER rely on unobservable opponent private state** (shed/backpacks are hidden).
5. **NEVER plant 50+ short-cycle Carrots** (paralyzes workers with tilling/replanting).
6. **NEVER modify `submission.py` directly without gauntlet proof**.

---

## 20. Most Promising Unresolved Research Questions

1. **The Day 8 Solvency Floor**: Can raising `land_reserve` from $800 to $1,200 on Days 6–8 eliminate the $509 liquidity canyon and raise our $29k–$38k floor without slowing compounding?
2. **Melon Opening Phase-Out**: Can replacing the second cycle of opening Melons on Day 12 with Strawberry/Cow investments eliminate the Day 24 $1 Melon crash?
3. **Market-Responsive Crop Dampening**: Can we cap Strawberry allocation at 26–28 plots and allocate remaining plots to Cows/Sheep and Wheat to prevent total collapse during town strawberry gluts?
4. **Shed De-Congestion Cadence**: Can flushing shed inventory to town shops every turn starting on Day 26 prevent end-of-day harvest deletion?
5. **Position #0 Order Priority for High-Value Commodities**: Can we systematically place `SELL MILK` and `SELL STRAWBERRY` at Position #0 in the turn's market list to preempt shared-step opponent sales?

---

## Collective Summary & Definitive Takeaways

### 10 Strongest Validated Principles:
1. `[VALIDATED]` Realized market price capture is the primary determinant of terminal wealth in competitive matches.
2. `[VALIDATED]` Maintaining full labor (11 workers) through Day 29 is mandatory for endgame monetization.
3. `[VALIDATED]` Sizing on-farm feed wheat plots to cover 100% of animal consumption eliminates starvation risk.
4. `[VALIDATED]` Cows have a 1.5–2.5 day payback period when factoring in Care (+1 milk) and Fertilizer ($40–$55).
5. `[VALIDATED]` 3 unlocked quadrants (`NW`, `NE`, `SW`) represents the optimal physical capacity ceiling.
6. `[VALIDATED]` Land #4 is economically destructive (-$24,000 average lift due to walking distance).
7. `[VALIDATED]` 10-Melon opening provides vital early liquidity over the old 15-Melon opening.
8. `[VALIDATED]` Shed capacity is strictly 100; excess un-dropped harvests are permanently deleted at midnight.
9. `[VALIDATED]` Market prices follow asymmetric, commodity-specific elasticity curves ($T=100$ for Strawberry vs $T=400$ for Wheat).
10. `[VALIDATED]` Paired seat-swapped evaluation against active opponents is the only trustworthy validation mode.

### 10 Strongest Rejected Principles:
1. `[FALSIFIED]` Unilateral market preservation or batch capping to defend prices.
2. `[FALSIFIED]` Holding milk or strawberries to wait for higher price windows.
3. `[FALSIFIED]` Shutting down or reducing worker hiring on Day 29.
4. `[FALSIFIED]` Unconditional early Land #2 expansion before establishing operating cash.
5. `[FALSIFIED]` Depleting town wheat to starve opponent livestock.
6. `[FALSIFIED]` Over-diversifying into high-maintenance, short-cycle Carrots.
7. `[FALSIFIED]` Treating `max_yield = 4` as a lifetime plant yield cap.
8. `[FALSIFIED]` Expanding to Land #4.
9. `[FALSIFIED]` Solo GPU screening scores without shared order-book contention.
10. `[FALSIFIED]` Modifying live production code based on individual match variance.

### 5 Unresolved Questions with Strongest Evidence:
1. What exact minimum treasury floor on Days 6–10 prevents animal starvation without delaying Land 2?
2. Does phasing out Melons after Day 12 prevent the Day 24 $1 price collapse?
3. Does capping Strawberry plots at 26–28 and expanding Cows raise the $29k–$38k floor?
4. Can order queue ranking (Position #0 priority) recover the narrow losses ($244 and $1,249)?
5. Does continuous shed flushing on Days 26–29 prevent midnight inventory discard?

### 5 Mistakes That Would Regress RC2:
1. Re-introducing any labor reduction or hiring cap on Day 28–29.
2. Re-introducing market order batch caps or delayed selling rules.
3. Distorting the 36-plot Strawberry backbone with 40+ short-cycle Carrots.
4. Spending capital on Land #4.
5. Depleting treasury below $500 on Day 6–8.

### The Single Biggest Remaining Weakness in RC2:
**The Day 8 Liquidity Canyon ($509 cash) combined with Strawberry Monoculture Saturation.**  
When RC2 hits an adverse seed where Strawberry prices soften and opponent order contention spikes, RC2 has zero cash cushion on Day 8 to adapt, its 9 second-cycle Melons crash to $1, and its 37 Strawberries yield half their expected value, causing the bot to collapse from its $101k ceiling down to the $29k–$38k failure floor.
