# GLM 5.2 Re-Audit: Late-Game Production Retirement Hypothesis

> **Analyst**: GLM 5.2 (third re-audit pass)
> **Date**: 2026-08-27
> **Trigger**: EXP121 Step-Level Divergence Forensics results
> **New Evidence**: D.1 beats elite replay winner in 16/20 matches; 2 real elite wins in Cluster 51 show late-game crop retirement pattern
> **Authority**: READ-ONLY. D.1 remains FROZEN.

---

## Part 1: What EXP121 Actually Found

### The Headline Result

D.1 economically outperforms the recorded elite replay winner in 16 of 20 matches. Of the 4 "elite wins":
- Ep 93332287 (Cluster 87): +$53 — statistical tie
- Ep 92739218 (Cluster 84): +$385 — statistical tie
- Ep 91763966 (Cluster 51): +$22,299 — **real elite win**
- Ep 91764902 (Cluster 51): +$13,229 — **real elite win**

**Only 2 of 20 matches show a genuine elite advantage, and both are from Cluster 51.**

### The Cluster 51 Late-Game Signature

| Milestone | D.1 Strawberries | Elite Strawberries | D.1 Hands | Elite Hands | D.1 Money | Elite Money |
|---|---|---|---|---|---|---|
| D21 | 40 | 28-29 | 0 | 0 | $31k-37k | $31k-46k |
| D26 | 34 | 11-12 | 0 | 0 | $37k-81k | $52k-102k |
| D30 | 6 stranded | 0 stranded | 2 | 10 | $49k-120k | $62k-143k |

### The Pattern

1. **Days 1-20**: Both D.1 and elite agents run similar production (38-40 strawberry plots, 8 cows, 0 hands). D.1 actually has MORE money at D16 in 2 of 3 cases.

2. **Days 21-26**: Elite agents **reduce active strawberry plots from ~29 to ~12** (a 59% reduction). D.1 **keeps 34 plots active** (only 15% reduction from 40). Elite agents overtake D.1 in cash during this window.

3. **Days 27-30**: Elite agents **hire 10 workers** and **clear all stranded crops to 0**. D.1 hires only 2 workers and **finishes with 6 stranded crops** that never get harvested/sold.

### What This Means

The elite advantage is NOT in opening strategy, NOT in mid-game selling cadence, NOT in worker count during production. The advantage is in **late-game crop retirement and labor allocation**:

- Elite agents stop servicing/replanting strawberry plots that cannot mature before terminal
- They redirect labor to harvesting mature crops and clearing the farm
- They hire a burst of workers on Day 29-30 for terminal cleanup
- D.1 keeps planting/servicing doomed crops and finishes with deadweight stranded inventory

---

## Part 2: Is This Genuinely Different From Falsified Hypotheses?

### Comparison With Falsified H1 (Worker Reduction: 13 to 9)

| Dimension | Falsified H1 | New Hypothesis |
|---|---|---|
| Worker count | 9 workers ALL GAME (Day 0-30) | 0 workers Days 1-26, then 10 workers Day 27-30 |
| Production phase | Reduced labor during PEAK production | Full production preserved through peak |
| Late game | Still 9 workers at end | Labor BURST at end for cleanup |
| Mechanism | Less labor = less cost | Stop servicing doomed crops + labor burst for harvest |

**Verdict: GENUINELY DIFFERENT.** H1 reduced workers during production (disastrous). The new hypothesis adds workers at the END for cleanup while preserving production-phase labor.

### Comparison With Falsified H3 (Extended Planting: Day 18 to Day 26)

| Dimension | Falsified H3 | New Hypothesis |
|---|---|---|
| Planting cutoff | Keep planting through Day 26 | Stop planting earlier, retire doomed crops |
| Effect on crops | MORE crops active late (bad) | FEWER crops active late (good) |
| Labor allocation | Same labor spread over more crops | Labor concentrated on harvestable crops |

**Verdict: GENUINELY DIFFERENT.** H3 extended planting (more doomed crops). The new hypothesis RETIRES doomed crops (fewer stranded crops). These are opposite directions.

### Comparison With Falsified H4 (Continuous Selling)

| Dimension | Falsified H4 | New Hypothesis |
|---|---|---|
| What changes | Sell continuously during Days 10-25 | Stop planting/servicing doomed crops after Day 20 |
| Market interaction | More selling transactions | No change to selling |
| Production | No change to production | Change to late-game production |

**Verdict: GENUINELY DIFFERENT.** H4 was about selling cadence. The new hypothesis is about production retirement. They operate on different game mechanics entirely.

### Conclusion: This Is a Novel Mechanism

The late-game crop retirement hypothesis is **structurally distinct** from all 18 previously falsified directions. It:
1. Preserves D.1's maximum early/mid-game production (unlike H1, H3)
2. Does not alter selling behavior (unlike H4, EXP119)
3. Targets a game phase (Days 21-30) that no prior experiment has tested
4. Addresses deadweight loss (stranded crops) that D.1 currently suffers

---

## Part 3: The Causal Mechanism

### Why D.1 Finishes With 6 Stranded Crops

Looking at D.1's code:
- `strawberry_last_plant` = Day 18 (line 47 of submission.py)
- D.1 continues planting strawberries through Day 18
- Strawberry takes 10 days to first harvest, with ongoing yields every 2 days
- A strawberry planted on Day 18 first harvests on Day 28
- A strawberry planted on Day 17 first harvests on Day 27
- But the game ends at Step 720 (Day 30, Hour 0)

So strawberries planted on Day 18-20 may only get 1-2 harvests before terminal, and any planted after Day 20 cannot mature at all. D.1 keeps servicing these doomed plots, wasting labor that could harvest mature crops.

### Why Elite Agents Have 0 Stranded Crops

The Cluster 51 elite agents:
1. Stop planting/servicing strawberries after ~Day 20-21 (plots drop from 29 to 12)
2. Allow doomed plots to die off naturally (no watering = crop expires)
3. Redirect labor to harvesting mature crops
4. Hire 10 workers on Day 29-30 for a final harvest-and-liquidate sweep
5. End with 0 stranded crops — everything is harvested and sold

### The Economic Impact

In the 2 elite-win cases:
- Ep 91763966: D.1 $120,694 vs Elite $142,993 → $22,299 gap
- Ep 91764902: D.1 $49,536 vs Elite $62,765 → $13,229 gap

The stranded 6 crops represent:
- Lost harvest value: ~6 crops * ~4 units * ~$120/strawberry = ~$2,880 in direct lost harvests
- Lost labor efficiency: workers servicing doomed crops instead of harvesting mature ones
- Lost terminal liquidation: 6 stranded crops cannot be sold at Step 696

But the $22k gap is much larger than $2.9k — suggesting the mechanism is not just about the stranded crops themselves, but about the **labor reallocation cascade**: when workers stop servicing doomed crops, they can harvest mature crops earlier, sell earlier at better prices, and reinvest that cash sooner.

---

## Part 4: The 4-Candidate Distinguishing Experiment (EXP122)

### Design: Minimal Counterfactual That Isolates the Mechanism

The user asked for the smallest experiment that distinguishes between:
1. Fewer workers
2. Fewer active late-game crops
3. Better late-game worker allocation
4. Pure settlement variance

### EXP122: 4-Arm Late-Game Intervention

**Common backbone**: D.1 unchanged through Day 20 (full 13-worker production, 40 strawberry plots, 8 cows, normal selling). Only late-game behavior varies.

**Arm A — D.1 Control**: Unmodified D.1. Baseline.

**Arm B — Late Crop Retirement Only**: After Day 20, stop watering/servicing any strawberry plot that was planted after Day 14 (i.e., cannot complete 2+ harvests before terminal). Do NOT change worker count. Do NOT change hiring. Just stop sending workers to doomed plots.

**Arm C — Late Worker Burst Only**: Keep D.1's crop servicing unchanged. But on Day 28, hire workers up to 10 total (instead of D.1's default 2). Send all workers to harvest mature crops and clear stranded inventory.

**Arm D — Combined Retirement + Worker Burst**: After Day 20, retire doomed crops (Arm B) AND hire 10 workers on Day 28 (Arm C). Full late-game optimization.

### Telemetry

For each arm, track:
- Last successful harvest (step, day)
- Number of doomed immature crops at Day 21, 26, 30
- Worker utilization after Day 25 (tasks assigned vs idle)
- Cash at Day 21, 26, 30
- Terminal stranded crops (count and value)
- Final reward
- Win rate vs elite replay opponents

### What Each Outcome Would Mean

| Result | Interpretation |
|---|---|
| B > A, C > A, D > A | Late-game retirement is the mechanism (both paths help) |
| B > A, C = A | Fewer active late-game crops is the mechanism (not worker allocation) |
| B = A, C > A | Better worker allocation is the mechanism (not crop retirement) |
| B = A, C = A, D = A | Pure settlement variance — the Cluster 51 pattern is coincidental |
| D >> B and D >> C | The interaction effect (retirement + burst together) is the real mechanism |
| B < A | Retiring crops actively hurts — the stranded crops have non-zero expected value |

### Why This Is the Smallest Distinguishing Experiment

1. **Only 4 arms** (vs EXP118's 7 arms)
2. **Only late-game changes** (Days 21-30), so early/mid-game is identical across arms
3. **Each arm tests exactly one variable**: B = crop retirement, C = worker burst, D = interaction
4. **Uses existing infrastructure**: replay opponents from the 8,268 corpus, D.1 backbone unchanged
5. **20 elite replay matches per arm** = 80 total matches, feasible in one run

### Expected Match Count

- 20 elite replay episodes (the same ones from EXP121)
- 4 arms
- 2 seats (control for seat asymmetry)
- = 160 matches total

---

## Part 5: Implementation Notes

### How to Implement Late Crop Retirement (Arm B)

In the FactorizedAgent wrapper:
1. After Day 20, scan all strawberry tiles
2. For each tile, compute: `days_until_first_harvest = planted_day + 10 - current_day`
3. If `days_until_first_harvest > (30 - current_day)`: crop cannot mature → stop watering
4. If `days_until_first_harvest > 0 and (30 - current_day - days_until_first_harvest) < 2`: only 0-1 harvests left → deprioritize
5. Remove these tiles from the task list (don't send workers to water/fertilize them)
6. Redirect freed labor to harvesting mature crops

### How to Implement Worker Burst (Arm C)

1. On Day 28, override `_hire_target` to return 10 instead of D.1's default
2. Assign all hired workers to HARVEST tasks on mature crops
3. On Day 29-30, assign workers to SELL tasks for terminal liquidation

### How to Implement Combined (Arm D)

Both interventions simultaneously: retire doomed crops after Day 20 AND hire 10 workers on Day 28.

---

## Part 6: GLM 5.2 Final Assessment

### Confidence Assessment

| Question | Answer | Confidence |
|---|---|---|
| Is this mechanism genuinely novel? | YES — no prior experiment tested late-game crop retirement | HIGH |
| Is this mechanism structurally different from H1/H3? | YES — preserves production, targets endgame only | HIGH |
| Could the Cluster 51 pattern be coincidental? | POSSIBLE — only 2 real elite wins out of 20 | MEDIUM |
| Is the $22k gap fully explained by stranded crops? | NO — stranded crops explain ~$3k, the rest is labor cascade | MEDIUM |
| Should we run EXP122? | YES — this is the first hypothesis with a plausible causal mechanism | HIGH |

### The Key Insight

> **Every prior experiment tested whether changing D.1's STRATEGY would improve outcomes.**
> **This experiment tests whether changing D.1's ENDGAME CLEANUP would improve outcomes.**
>
> The 1200+ wall may not be a strategy problem at all. It may be a **terminal efficiency problem** — D.1 leaves value on the table at the end of every game by servicing doomed crops and under-hiring terminal labor.

### Risk Assessment

- **If EXP122 is positive**: We've found the mechanism. A small endgame overlay (crop retirement + worker burst) could be added to D.1 without touching any of the 7 frozen invariants. This is the least invasive possible change.
- **If EXP122 is null**: The Cluster 51 pattern is coincidental, and we've eliminated yet another direction. The wall is likely exogenous (matchmaking equilibrium, R3 from prior re-audit).
- **If EXP122 is negative**: Late-game crop retirement actively hurts (doomed crops have non-zero expected value through partial harvests). This would be informative but would close the door on this mechanism.

### Recommendation

**Run EXP122 immediately.** This is the highest-information experiment we've designed — it tests a novel mechanism with a clear causal story, uses minimal intervention, and the implementation is straightforward. If positive, it's the first actionable improvement candidate in 18+ experiments.
