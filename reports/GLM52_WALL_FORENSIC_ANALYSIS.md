# GLM 5.2 Independent Forensic Analysis: The 1200+ Rating Wall

> **Analyst**: GLM 5.2 (second researcher)
> **Date**: 2026-08-27
> **Status**: HYPOTHESIS ONLY — not validated against replay telemetry
> **Authority**: READ-ONLY. No access to `submission.py`. D.1 remains FROZEN.
> **Caveat**: I have not independently audited the 8,268-episode dataset. All conclusions are hypotheses pending replay validation.

---

## Part 1: Independent Causal Analysis of the 1200+ Wall

### Context Summary

From the available evidence:

| Dimension | D.1 Baseline | Elite Clusters (87, 59, 84, 73, 76) |
|---|---|---|
| Workers | 13 | 8–10 |
| Cows | 8 | ~10 |
| Sheep | 0 | ~4 |
| Planting Cutoff | Day 18 (Step 432) | Day 26–28 |
| Selling Pattern | Batch >=4, Step 696 terminal dump | 100+ mid-game sales (Days 10–25) |
| Quadrants | 3 | 3 (no expansion) |

From the Research Index, the critical finding:
> "High and low PPO MCV groups have **similar physical asset counts**; **market realization** is the larger observed separator."
> "Milk sell price ~$51 in low-MCV traces vs ~$175 in high-MCV traces."

This creates a fundamental tension: elite clusters have **different physical configurations**, but the research index says **physical production doesn't explain the gap** — market realization does. The central question is whether the behavioral differences **cause** better market realization or are merely **correlated** with it.

---

### Hypothesis H1: Worker Reduction (13 -> 8–10) Enables Cash Velocity

#### 1. Proposed Economic Mechanism

D.1 employs 13 workers at $50/day each = $650/day in wages (~$19,500 over 30 days). Reducing to 9 workers saves $200/day = $6,000 over the full game. This freed cash could be redirected toward:
- Earlier seed purchases (accelerating harvest cycles)
- Earlier livestock acquisition (compounding milk/wool revenue)
- Market participation (buying inputs at lower prices early)

The critical claim: in a **saturated duopoly**, the marginal value of the 10th–13th worker is not in production (which is near-saturated) but in **cash liquidity** for market participation. Fewer workers = more cash on hand = ability to buy seeds/animals at better prices and sell at better prices.

**Counter-argument from D.1 spec**: 12 workers miss periodic water ticks causing 24-step harvest delay (-$12,000 penalty). 9 workers would miss even more. This suggests worker reduction directly hurts strawberry production.

**Resolution**: The key question is whether the $6,000 wage savings + better market timing outweighs the production loss from missed water ticks. This depends on the **market regime** — in a high-pie seed ($190k), capturing 2% more market share (~$3,800) could exceed the production loss.

#### 2. Telemetry to Prove/Disprove

- **Per-step cash balance** for elite agents vs D.1 at Days 5, 10, 15, 20, 25
- **Water tick coverage rate** (% of tiles watered on time) for 9-worker vs 13-worker configurations
- **Harvest cycle count** (do 9-worker agents actually complete fewer full harvest waves?)
- **Seed purchase timing** (do elite agents buy seeds earlier with freed cash?)
- **Marginal cash velocity**: delta-cash/delta-step during Days 10–25 for both configurations

#### 3. Confounding Variables

- **Worker assignment efficiency**: 9 workers might be assigned more efficiently (less idle time), not just fewer. The elite agents might have better pathing, not fewer workers.
- **Seed regime**: High-pie seeds may make worker reduction viable where low-pie seeds would not.
- **Opponent interaction**: Fewer workers means less competition for town resources? (Unlikely to matter.)
- **Survivorship bias**: Elite agents that win with 9 workers may be the ones who got favorable seeds; the 9-worker configuration might lose badly on bad seeds but we only see the winners.
- **Causal direction**: Maybe elite agents hire fewer workers **because** they have more cash from better market sales, not the reverse.

#### 4. Minimum Counterfactual Experiment

Take D.1 and cap hiring at 9 workers (Arm B from EXP118). Run against:
- 9 elite cluster replay opponents (seat-balanced)
- 9 fresh random seeds (control)

Measure: terminal reward, market share %, cash timeline, water tick coverage, harvest wave count.

**Critical design requirement**: Must be seat-balanced and paired (both configurations play both seats against the same opponent). Solo screening is not predictive (per the durable lesson from EXP-0113 through EXP-0120).

#### 5. Information Value Ranking

**MEDIUM** (rank 3 of 5). The D.1 spec already has strong evidence that 12 workers causes production penalties. The hypothesis that 9 workers is better contradicts the production model. However, the market-realization angle (cash freed for better timing) is genuinely unexplored. The information value is in understanding the **tradeoff curve** between production loss and market timing gain, not in confirming/disconfirming the hypothesis per se.

---

### Hypothesis H2: Sheep Addition (+4) Creates Cross-Commodity Market Advantage

#### 1. Proposed Economic Mechanism

In a saturated duopoly, both players flood strawberry and milk markets, depressing prices. Adding 4 sheep introduces wool as a **third commodity stream** that:
- Faces less market congestion (fewer opponents sell wool)
- Provides daily cashflow ($40–60/day per sheep?) independent of the strawberry/milk price war
- Diversifies revenue, reducing dependence on a single depressed commodity

The research index notes wool is a "smaller contributor" to the wealth gap (+$3,451 wool gap vs +$63,170 milk gap). This could mean:
- Wool is genuinely less important (falsifying this hypothesis)
- OR wool's contribution is small in absolute terms but **catalytic** — it provides the liquidity bridge that enables better milk/strawberry timing

#### 2. Telemetry to Prove/Disprove

- **Wool sell price** in elite vs non-elite matches (is wool less price-depressed?)
- **Wool sell volume** and timing (do elite agents sell wool continuously during Days 10–25?)
- **Cash position when wool sales occur** (does wool revenue bridge a liquidity gap?)
- **Milk/strawberry sell timing relative to wool sales** (is there a pattern where wool cash enables holding milk for better prices?)

#### 3. Confounding Variables

- **Pasture space**: Sheep require pasture tiles. If they displace cows, the net effect could be negative. Need to verify spatial layout.
- **Seed regime correlation**: High-pie seeds might correlate with agents who happen to buy sheep, without sheep being causal.
- **Opponent archetype**: Some opponents may not sell wool, making it a free market; others might.
- **Cost of sheep**: If sheep cost $600 each (4 sheep = $2,400), the ROI depends on wool price x days of production. Need to verify the exact economics.

#### 4. Minimum Counterfactual Experiment

Take D.1 and add 4 sheep on Days 8–12 (Arm C from EXP118). Run paired seat-balanced matches against elite cluster opponents. Measure: wool revenue, milk/strawberry sell prices (did they improve?), terminal reward.

**Isolation requirement**: This must be tested **alone** (Arm C) and **in combination** (Arm F/G) to detect interaction effects. Sheep alone might not help; sheep + continuous selling might be synergistic.

#### 5. Information Value Ranking

**LOW-MEDIUM** (rank 4 of 5). The research index already shows wool contributes only $3,451 to the gap — small compared to milk ($63,170) and strawberry ($50,772). Unless wool is catalytic (enabling better timing), it's unlikely to be the primary cause. However, the **interaction** with continuous selling is unexplored and could be valuable.

---

### Hypothesis H3: Extended Planting Cutoff (Day 18 -> 26–28) Increases Terminal Production

#### 1. Proposed Economic Mechanism

D.1 stops planting at Day 18 (Step 432) to ensure the Step 696 liquidation buffer has time to clear. Elite agents continue planting through Day 26–28.

Each strawberry cycle is 72 steps. From Day 18 to Day 28 = 240 steps = 3.3 additional potential harvest cycles. At 38 tiles x $160/tile-cycle NPV, this could represent ~$20,000 in additional production.

**The tension**: D.1's spec says "Squeezing 8 full strawberry waves into 720 steps leaves only 2.0 steps of total terminal slack." If D.1 is already at maximum, how can elite agents plant more?

**Possible resolution**: D.1's 2-step slack calculation assumes **13 workers** and **Step 696 terminal dump**. If elite agents:
1. Use 9 workers (slower planting but more cash for seeds)
2. Sell continuously (no need for a 24-step terminal dump window)
3. Plant through Day 26 (the last harvest at Day 28 + 72 steps = Day 31, which fits within 30 days)

...then the extended planting is **enabled** by the other behavioral differences. This makes H3 potentially **non-causal in isolation** but **causal as part of a package**.

#### 2. Telemetry to Prove/Disprove

- **Last seed purchase step** for elite agents (confirm Day 26–28)
- **Harvest wave count** (do elite agents actually complete 9+ waves vs D.1's 8?)
- **Terminal shed inventory** (do elite agents have stranded inventory at Step 720?)
- **Step 696–720 sell volume** (do elite agents sell less at the end because they sold continuously?)
- **Per-harvest-cycle revenue** (is the 9th wave's revenue higher because prices are still good mid-game?)

#### 3. Confounding Variables

- **Seed availability**: Later planting requires seeds to be available in the town shop. If the shop is depleted, this doesn't work.
- **Market price at harvest**: The 9th wave harvested at Day 28 might face depressed prices if both players harvest simultaneously.
- **Terminal valuation**: The scoring function credits shed inventory at 100% spot price. If elite agents have unharvested or unshedded strawberries at Step 720, they lose that value.
- **Interaction with continuous selling**: Extended planting only makes sense if you don't need the 24-step terminal dump window, which requires continuous selling. H3 may be **non-separable** from H4.

#### 4. Minimum Counterfactual Experiment

Take D.1 and extend planting to Day 26 (Arm D from EXP118). Run paired matches. **Critical**: Also run Arm D combined with Arm E (continuous selling) to test whether extended planting requires continuous selling to avoid the terminal dump bottleneck.

**Factorial design**: 2x2 (planting cutoff: Day 18 vs Day 26) x (selling: terminal dump vs continuous). This isolates the main effect and the interaction.

#### 5. Information Value Ranking

**HIGH** (rank 2 of 5). This hypothesis directly tests whether the D.1 production model's "2-step slack" constraint is real or an artifact of the terminal-dump selling strategy. If extended planting + continuous selling yields more total harvest waves without stranded inventory, it challenges a core D.1 invariant. The information value is high because it could invalidate a frozen assumption.

---

### Hypothesis H4: Continuous Mid-Game Selling (vs Step 696 Dump) Maximizes Cash Velocity & Market Share

#### 1. Proposed Economic Mechanism

This is the **central hypothesis** and the one most aligned with the research index's finding that market realization (not production) is the separator.

D.1 sells in batches at the end (Step 696). Elite agents sell continuously during Days 10–25 (100+ sales events).

**Proposed causal chain**:
1. Continuous selling realizes cash **earlier** (Days 10–25 vs Day 29)
2. Earlier cash realization enables **reinvestment** (more seeds, animals, workers) during the productive mid-game
3. Continuous selling avoids **end-game market flooding** — when both players dump 180+ units at Step 696, prices crash. Selling earlier captures higher mid-game prices.
4. Continuous selling maintains **market presence** — capturing market share incrementally rather than in a single end-game burst

**The key insight**: The research index shows milk sell price is $51 (low-MCV) vs $175 (high-MCV). This 3.4x price difference is NOT explained by having more cows — it's explained by **when** the milk is sold. If D.1 dumps all milk at Step 696 alongside the opponent, the market is flooded and prices crash to ~$51. If elite agents sell milk continuously during Days 10–25 when the opponent isn't selling milk, they capture $175/unit.

**This hypothesis predicts**: Elite agents are NOT maximizing terminal production. They are maximizing **cash velocity** — the rate at which production is converted to realized cash at favorable prices.

#### 2. Telemetry to Prove/Disprove

- **Per-step sell price** for milk, strawberry, wool in elite vs D.1 matches
- **Sell volume timing** (histogram of when sales occur across the 720 steps)
- **Cash velocity** (delta-realized_cash / delta-production) during Days 10–25
- **Step 696–720 sell volume** comparison (do elite agents sell less at the end?)
- **Market price trajectory** (does the price crash at Step 696 when both players dump?)
- **Reinvestment timing** (do elite agents buy more seeds/animals during Days 10–25 with realized cash?)
- **Cumulative realized cash** at Day 15, 20, 25 (is elite cash ahead of D.1?)

#### 3. Confounding Variables

- **Opponent selling pattern**: If the opponent also sells continuously, the price advantage disappears. The $175 vs $51 gap might be driven by **opponent behavior**, not own behavior.
- **Seed regime**: High-pie seeds may have naturally higher mid-game prices, making continuous selling more profitable. Low-pie seeds might not.
- **Market order limit**: 10 transactions/step. Continuous selling uses market slots that could be used for buying. Need to verify no opportunity cost.
- **Slippage**: Earlier research (EXP-0129) found that "intervening price drift absorbs slippage savings." But EXP-0129 tested **micro-batching to reduce slippage**, not **continuous selling to capture price windows**. These are different hypotheses.
- **Survivorship**: Elite agents who sell continuously AND WIN are the ones we see. Agents who sold continuously and LOST are in the non-elite clusters. Need to check if continuous selling correlates with winning or just with elite cluster membership.

#### 4. Minimum Counterfactual Experiment

Take D.1 and add continuous mid-game selling (Arm E from EXP118). Run paired seat-balanced matches against elite cluster opponents.

**Critical measurements**:
- Milk/strawberry sell price per unit (hypothesis: should increase from ~$51 toward ~$100+)
- Terminal reward (hypothesis: should increase if cash velocity > production loss)
- Market share % (hypothesis: should increase)

**Essential control**: Run Arm E **alone** (continuous selling only, no other changes) to isolate the effect. Then run Arm F (full package) to measure interactions.

**Additional requirement**: Test against **multiple opponent archetypes** — not just elite cluster opponents. If continuous selling only helps against elite opponents (who also sell continuously), it might be an adaptation, not a universal improvement.

#### 5. Information Value Ranking

**HIGHEST** (rank 1 of 5). This hypothesis:
- Directly addresses the research index's central finding (market realization > production)
- Challenges a core D.1 invariant (Step 696 terminal dump)
- Has the largest potential upside ($63k milk gap + $50k strawberry gap = $113k of the wealth gap)
- Is testable in isolation (Arm E)
- Has NOT been directly tested (EXP-0114 tested sell *suppression*, not continuous selling; EXP-0129 tested micro-batching, not continuous liquidation)

The critical distinction: every prior sell-timing experiment tested **selling less** or **selling later**. This hypothesis tests **selling more, earlier, and continuously**. It is in the **opposite direction** from all falsified experiments.

---

### Hypothesis H5: Cow Expansion (8 -> 10) Increases Milk Market Share

#### 1. Proposed Economic Mechanism

D.1 caps at 8 cows ($1,280/day milk revenue). Elite agents have ~10 cows. Two more cows produce +$320/day = +$9,600 over 30 days.

**The tension**: The research index says milk **price** (not quantity) is the separator. More cows = more milk to sell. If both players flood the milk market, more milk could **depress** prices further.

**However**: If elite agents sell milk **continuously** (H4), the additional milk from cows 9–10 is sold at favorable mid-game prices rather than dumped at Step 696. In this case, more cows + continuous selling = more milk sold at $175/unit instead of $51/unit.

This makes H5 **non-separable** from H4. Cow expansion only helps if combined with continuous selling.

#### 2. Telemetry to Prove/Disprove

- **Cow count** at Day 10, 15, 20, 25 for elite agents (confirm 10)
- **Milk production rate** (does 10 cows produce proportionally more milk?)
- **Milk sell price** with 10 cows + continuous selling vs 8 cows + terminal dump
- **Pasture space utilization** (do 10 cows fit in the existing pasture, or does this require expansion?)

#### 3. Confounding Variables

- **D.1 spec says >8 cows exceeds grazing space** — this is a hard physical constraint that needs verification
- **Milk storage**: Does milk accumulate in the shed? If so, more cows might create inventory management problems
- **Interaction with H4**: Cow expansion without continuous selling could worsen the Step 696 dump
- **Cost of cows**: 2 additional cows = ~$1,200 investment. ROI depends on milk price x days of production.

#### 4. Minimum Counterfactual Experiment

Test 10 cows alone (likely neutral or negative per D.1 spec) AND 10 cows + continuous selling (Arm F variant). The factorial design:

| | 8 cows | 10 cows |
|---|---|---|
| Terminal dump | D.1 baseline | Cow expansion only |
| Continuous selling | Arm E | Full package |

This 2x2 design isolates the main effect of cows, the main effect of selling, and their interaction.

#### 5. Information Value Ranking

**LOW** (rank 5 of 5). The D.1 spec has strong evidence that >8 cows exceeds grazing space. The research index says milk price, not quantity, is the separator. Unless H4 (continuous selling) is confirmed first, cow expansion is unlikely to help and may hurt. Test only if H4 shows positive results.

---

## Part 1 Summary: Hypothesis Ranking by Expected Information Value

| Rank | Hypothesis | Info Value | Rationale |
|---|---|---|---|
| **1** | **H4: Continuous Mid-Game Selling** | **HIGHEST** | Directly addresses the $113k market realization gap. Untested in this direction. Challenges a core D.1 invariant. |
| **2** | **H3: Extended Planting Cutoff** | **HIGH** | Tests whether D.1's "2-step slack" is real or an artifact of terminal dumping. Non-separable from H4. |
| **3** | **H1: Worker Reduction** | **MEDIUM** | Tests production-vs-liquidity tradeoff. Contradicts D.1's water-tick model but explores unexplored cash-velocity angle. |
| **4** | **H2: Sheep Addition** | **LOW-MEDIUM** | Wool is a small contributor ($3.4k gap). Possible catalytic interaction with H4. |
| **5** | **H5: Cow Expansion** | **LOW** | Physical constraint (grazing space). Price, not quantity, is the separator. Only viable if H4 confirmed. |

### The Central Thesis

> **Elite agents are NOT maximizing terminal production. They are maximizing cash velocity — the rate at which production is converted to realized cash at favorable prices during Days 10–25.**
>
> D.1's architecture is optimized for **maximum physical output + terminal liquidation**. This is optimal against weak opponents (who don't compete for market share) but hits a wall against elite opponents who **capture market share incrementally** during the mid-game, realizing higher prices and reinvesting the cash.
>
> The 1200+ wall is not a production ceiling. It is a **market realization ceiling** caused by D.1's terminal-dump strategy flooding the market at Step 696, crashing prices to ~$51/unit, while elite agents have already sold at ~$175/unit during Days 10–25.

---

## Part 2: Falsification Audit — Which Hypotheses Are Already Dead?

> **Question**: Given existing EXP001–EXP117 results, which hypotheses have already been effectively falsified, and which still have genuine unexplored search space?

### Already Falsified (DO NOT REVISIT)

| Hypothesis Direction | Falsifying Experiments | Why It's Dead |
|---|---|---|
| **Sell suppression / delayed selling** | EXP-0113, EXP-0114 (-$8,126 MCV), EXP-0115, EXP-0116, EXP-0117, EXP-0118, EXP-0119, EXP-0120 | All tested selling LESS or selling LATER. All failed at Gate 1 (WR <= 52.2%). The direction is wrong — D.1 needs to sell MORE and EARLIER, not less and later. |
| **Micro-batch slippage reduction** | EXP-0129 (50/50 neutral), EXP-0131 (50/50 neutral) | Tested splitting large dumps into micro-batches to reduce slippage. Neutral because "intervening price drift absorbs slippage savings." This is NOT the same as continuous selling for price capture — it's about execution mechanics, not timing strategy. |
| **Melon hedge / crop diversification** | EXP-0140, EXP009, EXP021, EXP041, various phase experiments | Melons have 120-step cycle vs strawberry 72-step. Lower cash velocity. Mixed planting fragments worker pathing. Dead. |
| **Early clearance / terminal liquidation timing** | EXP-0139 (shed credited at 100% spot price), EXP-0148–0155 | Terminal shed inventory is credited at full value with zero slippage. Market selling at the end LOSES money to slippage. This means D.1's Step 696 dump is actually SUBOPTIMAL — it should keep inventory in the shed! But wait — the dump exists to clear inventory that exceeds shed capacity. Need to verify shed capacity. |
| **Simple secondary timing overlays** | EXP-0113 through EXP-0120 (all "regime-gated exit overlay" variants) | All 8 variants falsified at Gate 1. These were pricing overlays on top of D.1's existing schedule. None changed the fundamental sell architecture. |
| **Land #4 expansion** | EXP-0121 (4.3% WR), EXP-0124 (neutral), multiple phase reports | 4-land trajectories underperform 3-land. All PPO traces stop at 3 lands. Dead. |
| **Opponent inventory front-running** | EXP-0122 | Opponent shed is private state. Not observable. Invalid. |
| **Town wheat feed denial** | EXP-0123 | Town pool is 10,000 units. Cannot be exhausted. Invalid. |
| **Cow milk timing front-running** | EXP-0126 | 100% cycle synchronization, flat intraday price. Zero premium. Invalid. |
| **Market order sorting** | EXP-0143 | Simultaneous clearing. Sorting is mathematically invariant. Invalid. |
| **Cash reserve scaling** | EXP-0144 | Cash reserve exists only in unused fallback path. Zero blocked purchases in baseline. Invalid. |
| **Wheat feed price squeeze** | EXP-0146 | Self-inflicted cost inflation. APEX also buys wheat. Invalid. |
| **Pasture 2 early construction** | EXP-0138 | Worker transport hardcoded at Step 261. Building earlier doesn't help. Invalid. |
| **Adaptive rotation threshold tuning** | EXP-0141 | Symmetric self-play invariance. Falsified. |

### Still Alive (Genuine Unexplored Search Space)

| Hypothesis | Why It's Still Alive | What Hasn't Been Tested |
|---|---|---|
| **H4: Continuous mid-game selling (sell MORE, EARLIER)** | Every prior sell-timing experiment tested selling LESS or LATER. **No experiment has tested selling MORE and EARLIER.** EXP-0129 tested micro-batching (execution mechanics), not continuous liquidation (timing strategy). The direction is opposite to all falsified experiments. | Arm E from EXP118 is the first test of this. Has NOT been run yet (EXP118 is still running). |
| **H3: Extended planting + continuous selling interaction** | D.1's "2-step slack" assumes terminal dump (24-step window). If continuous selling eliminates the dump window, extended planting becomes feasible. No experiment has tested this **interaction**. | Factorial 2x2 (planting x selling) has not been run. EXP118 Arm D tests planting alone; Arm F tests the combination. |
| **H1: Worker reduction for cash velocity (not production)** | D.1's 13-worker invariant is justified by water-tick coverage. But no experiment has tested whether the cash freed by fewer workers enables better market timing that outweighs the production loss. The tradeoff curve is unexplored. | EXP118 Arm B tests 9 workers. Has NOT been run yet. |
| **H2: Sheep as catalytic liquidity bridge** | Wool is a small contributor in isolation ($3.4k gap). But no experiment has tested whether wool revenue **enables** better milk/strawberry timing by providing cash during price windows. The interaction with H4 is unexplored. | EXP118 Arm C tests sheep alone; Arm F tests the combination. |
| **The interaction space (H1xH2xH3xH4)** | No prior experiment has tested the **full elite signature package** as a coherent unit. Each prior experiment tested a single overlay on top of D.1's existing architecture. The elite agents play a **fundamentally different architecture**, not D.1 + overlays. | EXP118 Arms F and G test the combined package. This is the most important unexplored space. |

### The Critical Insight

> **The falsification record reveals a pattern**: every prior experiment added a **single overlay** on top of D.1's existing architecture (sell suppression, cash reserve, land expansion, etc.). All failed because they didn't change the **fundamental sell architecture**.
>
> The elite signature is not an overlay — it's a **different architecture**:
> - Fewer workers (different labor model)
> - More livestock diversity (different revenue model)
> - Extended planting (different production model)
> - Continuous selling (different market model)
>
> Testing these one at a time (as EXP118 Arms B–E do) may show each is neutral alone but **synergistic together**. The full package (Arm F/G) is the real test.
>
> **However**: if the full package also fails at Gate 1 (like all prior experiments), it would suggest that the elite signature is **not causal** — it's a **marker** for favorable seed regimes or opponent archetypes that happen to correlate with those behavioral patterns.

---

## Part 3: Prioritized Research Plan

### Phase 1: Wait for EXP118 Results (CURRENT)

EXP118 is testing Arms A–G against elite cluster opponents. The results will tell us:

| EXP118 Result | Interpretation | Next Step |
|---|---|---|
| Arm E (continuous selling) wins | H4 confirmed. Cash velocity is the mechanism. | Test H4 in isolation against diverse opponents (not just elite clusters) |
| Arm F (full package) wins but E alone doesn't | Synergistic interaction. The package is causal but no single factor is. | Factorial decomposition to find the minimal causal subset |
| All arms neutral/fail | The elite signature is NOT causal. It's a marker for favorable regimes. | Abandon behavioral copying. Focus on market regime detection and adaptation. |
| Arm D (extended planting) wins | H3 confirmed. Production ceiling was an artifact of terminal dump. | Test whether D.1's "2-step slack" invariant is real |

### Phase 2: Telemetry Validation (IF EXP118 SHOWS PROMISE)

If any EXP118 arm shows positive results, validate with replay telemetry:

1. **Per-step sell price extraction** from the 8,268-episode corpus
   - Compare milk/strawberry sell prices in elite vs non-elite matches
   - Verify the $51 vs $175 price gap
   - Check if the gap is driven by sell TIMING or by SEED REGIME

2. **Cash velocity analysis**
   - Compute delta-realized_cash / delta-production for elite vs D.1
   - Determine if elite agents are ahead in cumulative realized cash by Day 15, 20, 25

3. **Confounding check: seed regime stratification**
   - Split the corpus by seed economic pie (low/mid/high)
   - Check if the elite signature only appears in high-pie seeds
   - If so, the behavioral differences may be adaptations to favorable regimes, not causal mechanisms

### Phase 3: Minimum Counterfactual (IF TELEMETRY VALIDATES)

Run the winning EXP118 arm through the full 4-gate certification:
1. Gate 1: Exact replay on 46 loss seeds (>=60% WR)
2. Gate 2: Historical suite (50 seeds)
3. Gate 3: Frozen holdout (100 seeds)
4. Gate 4: Statistical judge (6-dimension certification)

**Only if all 4 gates pass** does the candidate get considered for submission.

### Phase 4: Interaction Decomposition (IF FULL PACKAGE WINS)

If Arm F (full package) wins but individual arms don't, run a 2^4 factorial design:
- Workers: 13 vs 9
- Sheep: 0 vs 4
- Planting: Day 18 vs Day 26
- Selling: Terminal dump vs Continuous

This 16-arm design identifies the minimal causal subset and any interaction effects.

---

## Final Warnings

1. **Do not assume higher Elo means higher terminal wealth.** The research index explicitly warns against this. Elite agents may win by capturing more market share at similar terminal wealth levels.

2. **Do not assume the elite signature is causal.** It may be a marker for favorable seed regimes. The only way to distinguish is counterfactual testing (EXP118) + telemetry validation.

3. **Do not modify production code.** D.1 remains FROZEN. All experiments use research copies only.

4. **Do not trust solo screening.** Every prior solo-screening result that looked promising failed at paired Gate 1. Seat-balanced double-run is mandatory.

5. **The $51 vs $175 milk price gap is the strongest clue.** If this gap is driven by sell timing (not seed regime), H4 is the answer. If it's driven by seed regime, the wall is exogenous and cannot be broken by behavioral changes.

---

> **GLM 5.2 Final Recommendation**: Wait for EXP118 Arm E and Arm F results. If Arm E shows positive results, prioritize H4 (continuous selling) for full gate certification. If only Arm F shows positive results, run the 16-arm factorial decomposition. If all arms fail, abandon behavioral copying and pivot to market regime detection.
