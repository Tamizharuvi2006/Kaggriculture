# Market Artifact Recovery Audit

**Date:** 2026-08-22  
**Mode:** read-only repository/artifact audit  
**Games run:** 0  
**Model or production changes:** 0

## Verdict

The existing raw Kaggriculture replay artifacts are materially richer than the derived step5b market-timing cache. The missing per-event market fields can be recovered offline for the recoverable raw replays without running another game.

The only qualification is terminology: raw replays do not contain an explicit `accepted`, `rejected`, or `preempted` outcome flag. Those outcomes can be reconstructed or classified from adjacent observations and the submitted action list, but `preempted` remains an inferred label rather than a native replay field.

This means another 7-minute game run is not needed to obtain the missing observability. The PPO submission should remain frozen.

## Raw Evidence Inspected

- `reports/step5b/old_loss_gauntlet/raw_replays/*/episode-*-replay.json`
- `data/replay/mcv_replay_dataset.json`
- `research/build_mcv_replay_dataset.py`
- `research/replay_parser.py`
- `reports/step3h/traces/step3h_real_action_traces/real_action_trace_seed_39000_steps_720.json`
- `data/logs/episode-90744327-agent-0-logs.json`

The raw historical replay object contains `configuration`, `info`, `rewards`, `statuses`, and `steps`. Each step contains one record per player with `action`, `observation`, `reward`, and `status`.

The replay configuration explicitly records `maxMarketOrdersPerTurn: 10`, `townCenterSellInterval: 24`, and the 720-step horizon. The raw observations include public farms/cash, shared market prices and inventory, and the acting player's private shed.

## Recoverability Matrix

| Requested field | Raw source | Recoverability | Notes |
|---|---|---|---|
| Opponent market actions per clearing step | `steps[t][0].action.market`, `steps[t][1].action.market` | Direct | Both player action records are stored for every step. |
| Queue/order position | Index within `action.market` | Direct | Position is recoverable as zero-based list index; the 10-order processing cap is in configuration. |
| Cash before sell | `steps[t][player].observation.farms[player].money` | Direct | Observation is the state presented for that step. |
| Cash after sell | Same field at `steps[t+1]` | Direct adjacent-state read | Must account for all actions processed in the transition. |
| Inventory before sell | `steps[t][player].observation.private.shed` | Direct | Private shed is present for the acting player. |
| Inventory after sell | Same field at `steps[t+1]` | Direct adjacent-state read | Product-level shed delta is available. |
| State before order | Full `steps[t][player].observation` | Direct | Includes market, farms, private state, town, day/hour/step. |
| State after order | Full `steps[t+1][player].observation` | Direct adjacent-state read | The next observation is the post-transition state. |
| Price at decision | `steps[t][player].observation.market.prices` | Direct | Product-level spot price. |
| Resulting post-clearance price | `steps[t+1][player].observation.market.prices` | Direct adjacent-state read | The transition boundary must be aligned correctly. |
| Accepted/rejected sell | Action plus cash/shed/market deltas | Reconstructable | No explicit flag; infer whether requested quantity changed state and generated proceeds. |
| Preempted sell | Action-list position plus state/market deltas | Inferable, not explicit | Requires a deterministic classifier and careful handling of same-step multi-order effects. |
| Exact realized proceeds per order | Cash delta plus all same-step actions | Partially reconstructable | Exact attribution can be ambiguous when multiple market orders and other cash actions share a transition. |

## Important Difference From Current Derived Cache

`data/replay/mcv_replay_dataset.json` is sampled every ten steps and stores only a reduced tuple: player, step, cash, inventory, worker/tile counts, prices, one market action list, downstream wealth, and final wealth. It is useful for broad MCV analysis but is insufficient for exact per-event acceptance or queue forensics.

`research/build_mcv_replay_dataset.py` confirms that this reduction is intentional: it samples steps 50 through 640 at a ten-step interval and writes `executed_market_action`, not a full transition ledger. The raw `episode-*-replay.json` files retain the source information needed for a better offline extractor.

`research/replay_parser.py` further confirms that another existing parser reduces raw replays to action trajectories and terminal outcomes, so it also does not currently materialize the requested market ledger.

## What Can Be Answered Without New Games

Using the raw historical replays, an offline extractor can align, for each player and step:

1. both players' submitted market action lists;
2. each MILK/STRAWBERRY order's list position and requested quantity;
3. the acting player's pre-step cash and shed;
4. the next-step cash and shed;
5. shared price and market inventory before and after the transition;
6. day, hour, clearance position, and downstream wealth windows;
7. an inferred acceptance/rejection/partial-fill classification;
8. a cautious preemption-risk classification based on order position and observed state deltas.

That is enough to revisit the low-MCV market question without another game run, provided the result labels inferred outcomes clearly and validates baseline transition alignment first.

## What Cannot Be Claimed As Native Evidence

- The replay does not expose an authoritative per-order event log from inside the market processor.
- There is no native `accepted`, `rejected`, `preempted`, `queue_position_after_matching`, or `proceeds_for_order_id` field.
- A same-step action list can contain multiple orders, so cash and inventory deltas may need allocation rules.
- A low realized price alone cannot prove opponent causality; opponent action alignment is necessary.

## Final Boundary Decision

The artifact audit succeeds: the repository contains enough raw information to recover the requested market/queue observability offline. No new game is justified merely to obtain those fields.

However, this does not authorize building or running another diagnostic system now. The PPO, frozen single-file submission, v18 engine, reward logic, Land #4 behavior, checkpoints, and production files remain untouched. The milk-delay result remains rejected, and Land #4 remains unsupported as the fix.

