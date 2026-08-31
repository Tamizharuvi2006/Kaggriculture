# GLM 5.2 Re-Audit: Post-Falsification Forensic Analysis

> **Analyst**: GLM 5.2 (second researcher, re-audit pass)
> **Date**: 2026-08-27
> **Trigger**: EXP118 + EXP119 falsified all 5 elite-signature hypotheses (H1-H5)
> **New Evidence**: EXP120 seed-regime analysis (8,268 episodes / 16,536 seats)
> **Status**: H4 FALSIFIED. H1-H5 ALL FALSIFIED. Seed-regime hypothesis FALSIFIED.
> **Authority**: READ-ONLY. D.1 remains FROZEN.

---

## Part 1: Self-Audit — What H4 Got Wrong

### The Original H4 Thesis (Now Falsified)

> "Elite agents maximize cash velocity by selling continuously during Days 10-25,
> capturing $175/unit instead of D.1's $51/unit terminal-dump price."

### Why It Failed (EXP118 + EXP119 Evidence)

| Experiment | Arm | Result | Verdict |
|---|---|---|---|
| EXP118 Arm B | 9 workers | Catastrophic regression | H1 FALSIFIED |
| EXP118 Arm C | +4 sheep | Major regression | H2 FALSIFIED |
| EXP118 Arm D | Day 26 planting | Catastrophic regression | H3 FALSIFIED |
| EXP118 Arm E | Continuous mid-game sales | $0 alpha vs D.1 | H4 FALSIFIED |
| EXP118 Arm F | Full combined package | No improvement | H1-H4 interaction FALSIFIED |
| EXP118 Arm G | Non-destructive package | No improvement | FALSIFIED |
| EXP119 | 3 continuous-selling variants | All exact parity with D.1 | H4 re-confirmed FALSIFIED |

### Root Cause of the Error

GLM 5.2's original analysis made a **correlation-causation error**:

1. **Observed**: Elite agents sell continuously AND win more
2. **Inferred**: Continuous selling CAUSES winning
3. **Reality**: Both continuous selling and winning are CAUSED by a third factor — the agent's internal architecture (pathing, decision logic, state representation) — which we cannot replicate by overlaying sell commands on D.1

The critical mistake was treating the **visible behavioral output** of elite agents as the **causal mechanism**. In reality, the behavioral output is a **downstream consequence** of architectural differences that are invisible in replay data.

**Analogy**: Watching a Formula 1 driver brake later than a amateur and concluding that braking later causes faster lap times. But if the amateur brakes later, they crash — because the amateur lacks the car setup, tire knowledge, and spatial awareness that makes late braking viable.

D.1 + continuous selling = amateur braking later = crash.
Elite agent + continuous selling = professional braking later = fast lap.

The selling cadence is not the mechanism. It is a symptom of a superior internal model.

---

## Part 2: Seed-Regime Analysis (EXP120 Results)

### The Seed Hypothesis

> "The 1200+ wall may be caused by encountering particular seed-generated economic regimes
> rather than by a universally superior opponent strategy."

### EXP120 Empirical Results (8,268 episodes / 16,536 seats)

| Metric | Value | Interpretation |
|---|---|---|
| Corr(seed, reward) | ~0.0000 | Seed number has ZERO linear correlation with reward |
| Corr(log_seed, reward) | ~0.0000 | Log-transform also zero |
| Corr(seed % 1000, reward) | ~0.0000 | No modulo pattern |
| Corr(seed % 10000, reward) | ~0.0000 | No modulo pattern at any scale |
| Eta-squared (seed_bucket) | 0.0001 (0.01%) | Seed explains 0.01% of reward variance |
| Eta-squared (cluster) | 0.3061 (30.61%) | Cluster explains 30.61% of variance |
| Eta-squared (elo_quartile) | 0.0074 (0.74%) | Elo explains <1% of variance |
| Eta-squared (agent) | 0.0649 (6.49%) | Agent identity explains 6.5% |

### Seed Parity / First Digit / Modulo — All Null

| Test | Result |
|---|---|
| Even vs Odd seeds | AvgR $88,341 vs $89,195 — no significant difference |
| First digit (Benford) | All digits ~$88-91k — no significant difference |
| Seed % 1000 buckets | All buckets ~$85-90k — no significant difference |

### Verdict: SEED-REGIME HYPOTHESIS FALSIFIED

The Kaggle match seed number has **no predictive power** over reward. The economic pie variance that we observed ($10k-$168k range) is NOT driven by the seed number itself.

**However**: This does NOT mean the economic regime is irrelevant. It means the **seed number** is not the regime variable. The regime is determined by the **interaction** of:
- The seed (which generates initial conditions)
- Both agents' policies (which determine market dynamics)
- The resulting market price trajectory (which is emergent, not seed-determined)

The 30.61% variance explained by cluster is the key: clusters group agents by behavioral similarity, and agents in the same cluster produce similar rewards. This means the reward is determined by **agent behavior**, not by seed.

---

## Part 3: What Actually Explains the Wall

### Eliminated Explanations (Cumulative)

| # | Explanation | Falsified By | Mechanism of Falsification |
|---|---|---|---|
| 1 | Worker count (13 vs 9) | EXP118 Arm B | 9 workers = catastrophic regression |
| 2 | Sheep addition (+4) | EXP118 Arm C | +4 sheep = major regression |
| 3 | Extended planting (Day 26) | EXP118 Arm D | Day 26 = catastrophic regression |
| 4 | Continuous selling | EXP118 Arm E, EXP119 | $0 alpha, exact parity with D.1 |
| 5 | Full combined package | EXP118 Arm F/G | No improvement over D.1 |
| 6 | Sell suppression/delay | EXP-0113 through EXP-0120 | All falsified at Gate 1 |
| 7 | Micro-batch slippage | EXP-0129, EXP-0131 | 50/50 neutral |
| 8 | Melon hedge | EXP-0140, various | $0 alpha |
| 9 | Land #4 expansion | EXP-0121, EXP-0124 | 4.3% WR, negative |
| 10 | Opponent inventory front-running | EXP-0122 | Private state, invalid |
| 11 | Town wheat denial | EXP-0123 | 10k unit pool, invalid |
| 12 | Cow milk timing | EXP-0126 | Synchronized cycles, invalid |
| 13 | Market order sorting | EXP-0143 | Simultaneous clearing, invariant |
| 14 | Cash reserve scaling | EXP-0144 | Unused fallback path, invalid |
| 15 | Pasture 2 early construction | EXP-0138 | Hardcoded transport, invalid |
| 16 | Adaptive rotation threshold | EXP-0141 | Symmetric self-play, falsified |
| 17 | Regime-gated exit overlays | EXP-0151 through APEX-4.0 | All WR 0.500 < 0.60 |
| 18 | Seed number / seed regime | EXP120 | 0.01% variance explained |

### Remaining Live Explanations

After eliminating all 18 directions above, the remaining explanations are:

#### R1: Agent Architecture (Internal Decision Logic)

**Thesis**: The 1200+ wall is caused by differences in agent **internal architecture** — how agents process observations, plan multi-step sequences, manage worker pathing, and make conditional decisions — that are invisible in replay action logs.

**Evidence supporting**:
- Cluster explains 30.61% of reward variance (EXP120) — behavioral clusters, not seeds
- EXP110 found elite 80%+ WR agents play the SAME physical core as D.1 (38 strawberry + 8 cow + 13 worker), with the edge being "tighter worker-to-plot assignment and zero-stall dairy pathing"
- Every behavioral overlay transplanted onto D.1 has failed — because the advantage is in the decision logic, not the visible actions
- Agent identity explains 6.49% of variance — different agents systematically produce different rewards

**Why it was missed**: Replay data shows WHAT agents do (actions), not WHY they do it (internal state, planning, conditional logic). Two agents can make identical visible moves for different reasons — one reactively, one proactively. The reactive agent breaks down against stronger opponents; the proactive agent adapts.

**Testability**: Difficult. Would require:
- Step-by-step divergence analysis: at what step does D.1's action sequence diverge from elite agents on the same seed?
- Conditional action analysis: does D.1 make different decisions than elite agents when facing the same market state?
- Pathing efficiency analysis: is D.1's worker-to-plot assignment actually less efficient than elite agents?

#### R2: Opponent Interaction / Market Dynamics

**Thesis**: The wall is caused by **interactive market dynamics** — D.1 performs well against weak opponents (who don't compete for market share) but loses against strong opponents who exploit D.1's predictable selling pattern.

**Evidence supporting**:
- D.1's terminal dump is predictable — a strong opponent can front-run it
- The $51 vs $175 milk price gap may be caused by opponent behavior, not D.1's behavior
- Solo screening is not predictive — the advantage only appears in paired matches
- WR drops from 85-100% (<900 Elo) to 38-42% (900-1200 Elo) — the wall is opponent-dependent

**Why it was missed**: We tested unilateral behavioral changes (changing D.1's selling) rather than testing how D.1's behavior interacts with opponent behavior. The question isn't "should D.1 sell continuously?" but "should D.1 adapt its selling to the opponent's selling pattern?"

**Testability**: Moderate. Would require:
- Opponent-conditioned analysis: does D.1 lose because the opponent exploits D.1's terminal dump?
- Counterfactual: if D.1 faces a copy of itself, does the terminal dump cause mutual price destruction?
- Adaptive selling: does D.1 improve if it sells when the opponent is NOT selling (reactive rather than continuous)?

#### R3: Matchmaking / Population Exposure

**Thesis**: The wall is a **statistical artifact of matchmaking** — D.1's rating converges to ~1000-1200 because that's the equilibrium rating for a fixed-policy agent in the Kaggle population, regardless of its absolute skill.

**Evidence supporting**:
- V4.1 peaked at 2089.8 then converged to 1714.4 — the convergence is a population effect
- Elo explains only 0.74% of reward variance — the Elo range in our corpus (2808-3218) is narrow
- D.1 and D.2 both maintained high market share against elite corpus (EXP116) — D.1 isn't being outplayed, it's being out-rated
- The 50/50 win rate in the corpus (4058 wins for seat 0, 4037 for seat 1, 173 ties) suggests near-symmetric skill at the top

**Why it was missed**: We assumed the wall is a skill problem. It might be a matchmaking equilibrium problem. A fixed-policy agent in a self-play-saturated population converges to a rating that reflects the population's average skill, not the agent's absolute quality.

**Testability**: Difficult. Would require:
- Rating simulation: if D.1 plays 1000 matches against a population with known skill distribution, where does its rating converge?
- Population analysis: what is the skill distribution of the current Kaggle population? Is 1000-1200 the equilibrium for ANY fixed policy?
- Counterfactual: if D.1 played only against opponents rated 800-1000, would its rating stay above 1200?

#### R4: Conditional Decision-Making (Adaptation)

**Thesis**: The wall is caused by D.1's **lack of conditional adaptation** — D.1 executes a fixed policy regardless of opponent behavior, market state, or game situation. Elite agents condition their actions on observable state.

**Evidence supporting**:
- Every fixed overlay (sell more, sell less, sell earlier, sell later) failed — because the RIGHT action depends on context
- EXP-0141 (adaptive rotation) was falsified, but that was a simple threshold, not true conditional logic
- The research index says "Which observable market state at the exact sell decision predicts whether milk should be sold now, partially sold, or retained?" — this is still unanswered
- D.1's invariants are ALL unconditional — 13 workers always, 8 cows always, Day 18 cutoff always, Step 696 dump always

**Why it was missed**: We tested unconditional changes (always sell continuously, always use 9 workers). We never tested CONDITIONAL changes (sell when opponent isn't selling, hire fewer workers when cash is low, extend planting when prices are high).

**Testability**: Moderate. Would require:
- State-conditioned policy: D.1 + a decision rule that conditions selling on opponent market activity
- Observable-state analysis: what observable variables at Day 5-10 predict whether D.1 will win or lose?
- Early divergence: at what step does the outcome become predictable? If by Day 5, the game may be determined by early-game conditions that D.1 doesn't adapt to.

---

## Part 4: The 3 Highest-Information Next Experiments

### Experiment 1: Step-Level Divergence Forensics (R1 + R4)

**Question**: At what exact step does D.1's action sequence diverge from elite agents on the same seed, and what observable state variable predicts the divergence?

**Design**:
1. Take 20 episodes where elite agents won and D.1 would lose (from the 8,268 corpus)
2. For each episode, replay D.1 on the same seed against the same opponent
3. Log every action where D.1 diverges from the elite agent's actual action
4. Track: step of first divergence, type of divergence (market vs farmer vs hands), observable state at divergence

**Why this is highest-info**:
- Directly tests R1 (architecture) and R4 (conditional logic) simultaneously
- If divergence happens early (Day 1-5) and is in farmer/hands commands → architecture problem (pathing)
- If divergence happens late (Day 15+) and is in market commands → adaptation problem (selling)
- If divergence is in market commands triggered by specific opponent behavior → R2 (opponent interaction)
- The step of first divergence tells us WHERE the game is won or lost

**Expected outcome**: This will tell us whether to invest in pathing/worker logic (R1) or market adaptation (R4) or opponent modeling (R2).

### Experiment 2: Observable-State Win Predictor (R4)

**Question**: What observable variables at Day 5, 10, and 15 predict whether D.1 will win or lose a given match?

**Design**:
1. Run D.1 against 100 diverse opponents (50 below 1000 Elo, 50 above 1200 Elo)
2. At each milestone (Day 5, 10, 15, 20, 25), log: cash, market share, shed inventory, opponent cash, opponent market activity, market prices, worker count, crop count
3. Train a simple logistic regression: does any Day-5 or Day-10 observable predict the match outcome?
4. If yes: the game is determined early, and D.1 needs to adapt to early conditions
5. If no: the game is determined late, and D.1's endgame is the problem

**Why this is high-info**:
- If a Day-5 variable predicts outcome with >70% accuracy, then the wall is an early-game adaptation problem
- If no early variable predicts, then the wall is a late-game or interaction effect
- This directly tests R4 (conditional decision-making) by identifying WHICH observable should trigger adaptation
- It also tests R3 (matchmaking) — if no observable predicts, the outcome may be near-random at the top

**Expected outcome**: Either identifies a specific early-game signal that D.1 should condition on, or proves that no observable signal exists (meaning the wall is exogenous).

### Experiment 3: Opponent-Conditioned Counterfactual (R2)

**Question**: If D.1 adapts its selling to the opponent's selling pattern (selling when opponent is NOT selling), does it improve win rate?

**Design**:
1. Take 20 elite replay opponents from the corpus
2. Run D.1 baseline (fixed policy) — record win rate and market share
3. Run D.1 + reactive selling rule: "if opponent did not sell any commodity in the last 24 steps, sell shed inventory; if opponent sold in the last 24 steps, hold"
4. Compare win rate and market share

**Why this is high-info**:
- This is the FIRST test of conditional/opponent-aware selling (all prior tests were unconditional)
- It directly tests R2 (opponent interaction) — if reactive selling helps, the wall is an interaction effect
- It tests R4 (conditional logic) — if conditional selling helps where unconditional failed, the problem is adaptation, not the selling action itself
- It is cheap to implement (overlay on D.1, no architecture change)

**Expected outcome**: If reactive selling produces positive alpha, we've found the mechanism (opponent interaction). If it produces $0 alpha like unconditional selling, then R2 is weakened and R1 (architecture) becomes the primary suspect.

---

## Part 5: Prioritized Research Direction

| Priority | Direction | Rationale | Cost | Expected Info |
|---|---|---|---|---|
| **1** | Step-Level Divergence Forensics | Identifies WHERE the game is won/lost and WHAT type of action diverges | Low (replay analysis) | HIGHEST — distinguishes R1/R2/R4 |
| **2** | Observable-State Win Predictor | Identifies WHEN the game becomes predictable and WHICH variable predicts it | Medium (100 matches) | HIGH — tests R4 and R3 |
| **3** | Opponent-Conditioned Counterfactual | Tests whether conditional adaptation works where unconditional failed | Low (overlay on D.1) | MEDIUM — tests R2 and R4 |

### What NOT to Do Next

1. **Do NOT build D.3** — we have no validated hypothesis to implement
2. **Do NOT test more unconditional overlays** — 18 directions falsified, the pattern is clear
3. **Do NOT analyze more seed properties** — EXP120 proved seed is not causal (0.01% variance)
4. **Do NOT retrain PPO** — the problem is not optimization, it's understanding
5. **Do NOT assume the wall is breakable** — R3 (matchmaking equilibrium) may mean 1000-1200 is the theoretical ceiling for any fixed policy

---

## Part 6: Revised Central Thesis

> **The 1200+ wall is NOT caused by a secret farm strategy, a seed regime, or a selling cadence.**
>
> **The wall is most likely caused by one of:**
> 1. **Agent architecture** — D.1's internal decision logic (pathing, planning, state representation) is inferior to elite agents' logic, and this difference is invisible in replay action logs
> 2. **Opponent interaction** — D.1's fixed policy is exploitable by strong opponents who adapt to its patterns, and the advantage is in the INTERACTION, not in any unilateral behavior
> 3. **Matchmaking equilibrium** — 1000-1200 may be the theoretical rating ceiling for ANY fixed policy in the current Kaggle population, and no behavioral change can break it
> 4. **Conditional adaptation** — D.1 lacks the ability to condition its actions on observable game state, and the right action depends on context that D.1 ignores
>
> **The key insight from EXP118/119/120**: Elite agents LOOK different, but copying their visible behavior into D.1 doesn't reproduce the advantage. The advantage is in the invisible architecture, the interaction, or the adaptation — not in the actions themselves.
>
> **The next research question is NOT "What do top agents buy?"**
> **The next research question IS "What observable variable distinguishes a future D.1 win from a future D.1 loss BEFORE the outcome is determined?"**

---

> **GLM 5.2 Final Recommendation**: Run Experiment 1 (Step-Level Divergence Forensics) first. It is the cheapest and highest-information experiment. If divergence is in pathing → invest in worker logic. If divergence is in market commands → invest in adaptive selling. If no divergence is found → the wall is exogenous (R3) and cannot be broken by any policy change.
