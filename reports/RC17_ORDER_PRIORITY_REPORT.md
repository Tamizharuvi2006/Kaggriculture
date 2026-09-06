# RC17: Slot-0 Sell Priority (paired official simulator)

**Date**: 2026-09-06  
**Control**: RC15 (`submission_rc15.py`) — previous production  
**Candidate**: RC17 (`submission_rc17.py`) — now copied to `submission.py`  
**Simulator**: `kaggle_environments` 1.32.7, `townCenterSellInterval=24`, 720 steps, seat-swapped, 10 workers  

This is **not** another production rewrite. It is one market-queue change.

## Why everything else kept failing

Live TrueSkill is binary W/L. Mid-tier losses are mostly **<$3,500 coin-flips** on a shared order book. Extra plants, extra cows, PPO, and “hold for price” all dump or starve the same pie and collapse to ~50% WR once both seats share the market.

RC16 (remove Day-10 animal freeze) **reproduced that failure**:

| Gate | Matches | WR | Mean Δ | Animals |
|---|---:|---:|---:|---:|
| RC16 vs RC15 | 60 | **50.0%** | **−$1,031** | 11.6 vs 8.7 |

Herd completed. Milk glut. No wins. Falsified. File kept as `submission_rc16.py`.

Day-29 hire=6 is also **not** the leak on this chassis: by Day 28 yield is already 0 and the shed is empty. Do not spend research there again.

## The actual lever

Dawn dumps (`hour == 1`) fill the **10-order cap**. RC15 put `SELL FERTILIZER` in slot 0 (~23 first-sells vs 5 milk). The book is interleaved slot-by-slot. Fertilizer at $40–$50 was clearing before milk/strawberry.

RC17 only reorders sells:

`MILK → STRAWBERRY → WOOL → MELON → other crops → FERTILIZER → wheat surplus`

Same quantities. Same farm. No new holds, caps, or animals.

## Official paired results vs RC15

| Suite | Seeds | Matches | W–L | WR | Mean Δ | Median Δ |
|---|---:|---:|---|---:|---:|---:|
| Discovery (seed 2000, ×137) | 30 | 60 | **41–19** | **68.3%** | **+$1,696** | **+$2,176** |
| Holdout (seed 9000, ×137) | 30 | 60 | **37–23** | **61.7%** | **+$943** | **+$1,960** |
| **Combined** | **60** | **120** | **78–42** | **65.0%** | **+$1,320** | — |

Discovery seat split: 21/30 seat 0, 20/30 seat 1. Both-win seeds 17 vs both-loss 6. One-sided binomial P(W≥41 | 50%) ≈ **0.003**.

Razor band on discovery (`|Δ| < $3,500`): **16 wins vs 7 losses**. That is the rating-relevant band.

## What this does *not* do

RC15 and RC17 both go **0–20 vs `kaitofukami-v18`** (~−$50k). This lineage is not V4.1. Do not claim 1700+ or 2000 Elo from this patch. The patch is an edge against **RC15-like economic bots** that waste slot 0 on fertilizer.

Do not stack RC16’s extra animals on top of RC17. That glut already lost.

## Rollback

```bash
cp submission_rc15.py submission.py
```

## Next (only if live losses share a cause)

1. Submit `submission.py` (RC17) and watch **W/L on <$3.5k games**, not mean coins.
2. If live opponents already put milk first, this edge shrinks — do not add volume.
3. Do not reopen Land #4, milk-hold, Day-29 labor cuts, or solo GPU screens.
