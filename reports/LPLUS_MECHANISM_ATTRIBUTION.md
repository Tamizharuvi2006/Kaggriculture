# V4.1 to L+ Mechanism Attribution Audit

**Date:** 2026-08-22  
**Scope:** Read-only attribution using existing repository reports, cached traces, and prior paired results.  
**New games:** None run.  
**Source changes:** None.  
**Artifacts protected:** V4.1, L+, PPO, OPT-7, and sealed production files.

## Executive Summary

The authoritative L+ delta is two small changes on top of fixed V4.1:

1. Increase `opening_melons` from 9 to 10.
2. When MILK price is at least 230, rank valid market sales as MILK first, then MELON, STRAWBERRY, WHEAT, then other products.

The existing factorial benchmark provides quantitative attribution. On that benchmark, the opening-melon change has the larger standalone main effect, while the MILK-first ranker directly addresses the documented queue-preemption failure. Their measured interaction is small, so the combined result is mostly additive rather than evidence of a strong nonlinear synergy.

The exact contribution of either change to the live Kaggle score cannot be claimed from local experiments alone. The live L+ result is evidence for the combined implementation, not a factorial Kaggle attribution.

## Source-Level Deltas

The authoritative lineage report identifies:

- V4.1: `baseline/kaitofukami-v18.py`
- L+: `generalization_pipeline/submission_candidate_l_plus.py`
- L+ preserves the fixed-v18 schedule and the surrounding liquidity, production, lifecycle, and safety logic.
- The separate `use_fixed_schedule=False` experiment is not part of the final authoritative L+ source.

The two confirmed L+ changes are therefore the opening liquidity change and the MILK-first queue ranker. Later Day 12-15 reinvestment and fleet differences are downstream consequences, not separate L+ code deltas.

## Factorial Attribution

Existing artifact: `research_results/authoritative_master_baseline_results.json`.

| Configuration | Opening melons | MILK ranker | Mean final MCV | Mean margin | Win rate |
|---|---:|---:|---:|---:|---:|
| V4.1 baseline | 9 | Off | 80,544.42 | 715.72 | 27.0% |
| Opening change only | 10 | Off | 90,399.59 | 4,961.27 | 80.0% |
| MILK ranker only | 9 | On | 86,615.33 | 12,487.09 | 99.0% |
| Combined L+ deltas | 10 | On | 96,686.78 | 16,019.90 | 100.0% |

Using mean final MCV:

- Opening-melon main effect versus baseline: **+9,855.17**.
- MILK-ranker main effect versus baseline: **+6,070.91**.
- Two-factor interaction: **+216.28**.

The same calculation on mean margin gives approximately:

- Opening-melon main effect: **+4,245.55**.
- MILK-ranker main effect: **+11,771.37**.
- Interaction: **-712.74**.

These numbers are local benchmark attribution, not a direct decomposition of the live Kaggle leaderboard score. The existing paired L+ versus V4.1 result, including its reported mean advantage of **+15,604.6**, evaluates the combined L+ state and cannot allocate that live/synthetic paired advantage between the two changes without a matched factorial evaluation of that exact environment.

## Historical Failure Modes Addressed

### Opening liquidity

The V4.1 analysis documents early cash starvation: opening with 15 melons in the older comparison left insufficient early liquidity and delayed follow-on investment. In the authoritative L+ lineage the relevant code change is the narrower `opening_melons: 9 -> 10` adjustment. Its measured standalone effect is the larger final-MCV main effect in the factorial benchmark.

### Market queue preemption

The V4.1 analysis documents unranked market orders allowing high-volume products to displace MILK. The L+ ranker gives MILK priority when price is at least 230, followed by MELON, STRAWBERRY, WHEAT, and other products. This directly targets the documented competitive failure in which MILK was not placed first. Its standalone effect is especially strong on mean margin and win rate.

### Day 12-15 reinvestment

Existing replay dissections show that stronger Day 12 liquidity and Day 15 reinvestment correlate with larger fleets and better terminal MCV. This is downstream evidence of the two L+ deltas and should not be recorded as a third independent L+ mechanism.

## Interaction

The factorial MCV interaction is only **+216.28**, small relative to both main effects. This supports the conclusion that the combined gain is predominantly additive in the existing benchmark. The margin interaction is mildly negative, so there is no evidence here that combining the two changes creates a large special synergy.

## Current Frozen v18/PPO Coverage

Based on the inspected source lineage:

- Frozen v18 retains the pre-L+ opening value and does not contain the authoritative L+ MILK-first ranker.
- The PPO path is an adapter over the v18 behavior and exposes bounded `u_market` and `u_route` controls at decision step 120. Those controls do not, by themselves, add the L+ opening-melon change or the explicit L+ MILK-first ranker.
- Therefore the frozen PPO candidate should not be described as containing the L+ mechanisms unless its exact packaged source is separately shown to embed them.

## Recommendation

The smallest evidence-backed mechanism to test first is the **MILK-first ranker alone**:

- It is a narrow ordering change over already-valid market actions.
- It directly addresses the documented queue-preemption failure.
- It has strong standalone win-rate and margin evidence in the existing factorial artifact.
- It leaves opening quantities, affordability, liquidity reserves, production, and lifecycle behavior unchanged.

The opening-melon change is the next isolated candidate and has the larger standalone final-MCV effect. It should remain a separate experiment, not be combined with the ranker in the first attribution follow-up.

No new run is required to complete this audit. Any future validation should be a separately authorized, paired experiment with the V4.1 and L+ artifacts preserved.
