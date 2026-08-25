# V4.1 to L+ Lineage Reconstruction

## Scope

Read-only reconstruction from repository artifacts, source builders, replay
reports, Kaggle submission records, and existing benchmark results. No games,
training, optimization, submission, or production-file changes were performed.

## Executive Summary

L+ was a small, targeted modification of the proven V4.1 implementation, not
a replacement engine. The final L+ source preserves the V4.1/v18 closed-loop
engine, state-repair behavior, fixed schedule, animal/crop lifecycle, land
progression, and v13 market machinery. The documented L+ delta is:

1. Increase `opening_melons` from 9 to 10.
2. Add an opponent-aware market-order ranker that moves MILK SELL orders to
   the front when MILK price is at least 230, followed by MELON, STRAWBERRY,
   WHEAT, then other orders.

This is confirmed by the L+ builder and by a 25-line source diff against V4.1.

## Confirmed Artifacts

| Role | Artifact | Evidence |
| --- | --- | --- |
| V4.1 starting point | `baseline/kaitofukami-v18.py` | Frozen master; Kaggle ref `55249106`, public rating 1479.8 |
| L+ builder | `experiments/build_clean_candidate_l_plus.py` | Reads V4.1 and applies the two changes above |
| L+ final source | `generalization_pipeline/submission_candidate_l_plus.py` | Kaggle submission ref `55373932`, score 1254.1 |
| L+ backup | `generalization_pipeline/submission_candidate_l_plus_raw_backup.py` | Same SHA256 as final L+ |
| L+ loss analysis | `reports/LOSS_DIR_AUTHORITATIVE_COMPARISON.md` | Milk queue and fleet timing findings |
| Days 8-15 analysis | `reports/DAYS_8_15_ACTION_DISSECTION.md` | Melon liquidity, reinvestment, and queue findings |
| V4.1 weakness audit | `generalization_pipeline/v41_archetype_audit_results.json` | Cattle and capital-turtle weaknesses identified |

## Source-Level Delta

### Preserved from V4.1

- Full v18 action engine and fixed v18 schedule.
- State-repair and closed-loop action handling.
- Land expansion timing and worker/animal lifecycle.
- Crop and livestock production logic.
- v13 market adaptation and daily market gating.
- Affordability, order limits, and safety behavior.

### Added by final L+

- `opening_melons: 9 -> 10`.
- MILK-first order ranking when MILK price is at least 230.
- Secondary order ranking: MELON, STRAWBERRY, WHEAT, then remaining orders.

### Provenance discrepancy

`experiments/build_standalone_candidate_l_plus.py` documents an attempted
`use_fixed_schedule=False` modification. The final L+ artifact still contains
`use_fixed_schedule=True`, matching the clean builder and the actual submitted
source. Therefore the dynamic-schedule change is not part of the authoritative
L+ lineage.

## Why the Changes Were Introduced

The V4.1 weakness audit identified only 30% win rates against the cattle-rusher
and capital-turtle archetypes, with negative mean margins of approximately
3.9k and 4.9k respectively. The live loss analysis then identified two narrow
failure mechanisms:

- Market queue contention could displace MILK sales when high-volume WHEAT
  orders occupied the ten-order limit.
- Delayed conversion of Day-12 melon liquidity into the secondary livestock /
  crop portfolio reduced later STRAWBERRY and WOOL revenue.

The L+ changes address those findings conservatively: preserve the established
engine and schedule, improve opening liquidity, and protect the highest-value
market queue position.

## Evidence That L+ Worked

- Paired V4.1 comparison: 20/20 direct L+ wins, mean delta `+15,604.6`.
- Existing 400-match L+ screen: 100% win rate against the tested capital,
  cattle, market, and crop archetypes.
- Kaggle submission ref `55373932`: leaderboard score `1254.1`, the current
  competition champion.
- Authoritative live losses were narrow rather than catastrophic, generally
  within roughly 692 to 2,468 MCV, supporting the claim that L+ retained the
  strong V4.1 economic backbone.

## Later Branches and Rejections

L++, Hybrid V13, APEX 3.0, APEX 3.3, and APEX 3.5 are later experimental or
submission branches. Their lower Kaggle scores do not prove every individual
change was harmful, but they are not part of the minimal, verified L+ lineage.
The practical result is clear: none displaced L+ as the competition champion.

## What PPO Currently Lacks

The PPO candidate does not reproduce the whole L+ decision system. It applies
two controls at decision step 120 and delegates the rest to the v18 adapter.
Compared with L+, it lacks direct, explicit control over:

- the full opening-liquidity schedule,
- MILK queue priority and market-order composition,
- Day-12 to Day-15 fleet reinvestment timing,
- the complete production/sell cadence that created the L+ score.

That explains why a locally superior PPO research result did not translate into
the L+ Kaggle score: the learned controller sits above the proven policy but
does not own the specific high-impact mechanisms that differentiated L+.

## Smallest Credible Future Hypothesis

If work resumes, the only defensible next hypothesis is a new L+ lineage study:
reconstruct the exact V4.1-to-L+ artifact, then isolate one mechanism at a time,
starting with the MILK queue ranker and opening-liquidity change. PPO should not
be modified or retrained as part of that hypothesis.

## Frozen Decision

- L+ remains the competition champion.
- PPO remains research-only and frozen.
- V4.1 and L+ artifacts remain untouched.
- No new experiment is justified until a materially different hypothesis is
  explicitly approved.
