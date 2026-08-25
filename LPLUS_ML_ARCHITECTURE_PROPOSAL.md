# L+ + ML Research Architecture Proposal

Date: 2026-08-22
Scope: read-only architecture design. No training, games, source changes, checkpoint changes, or submission changes.

## Decision

Keep the proven L+ implementation as the execution and safety backbone. Add ML only as an optional, abstaining recommendation layer that selects among already-valid L+ market modes. The ML layer must never directly emit arbitrary farmer, hand, purchase, land, production, or market quantities.

```text
public observation + L+ candidate state
                    |
          small market-state model
                    |
  pressure/regime estimate + confidence + abstain
                    |
       L+ constrained recommendation hook
                    |
       L+ affordability and action sanitizer
                    |
                final action
```

The first research target is **market-pressure prediction for sell-order priority**, not PPO replacement and not general action prediction.

## Why this target

Existing evidence says:

- L+ is the strongest competition backbone and already contains the two validated narrow mechanisms: opening liquidity and high-price MILK-first ordering.
- Shared-market pressure and opponent strength explain much more of the absolute MCV range than land count or raw production.
- Generic milk holding, late milk timing, broad sale suppression, and direct unilateral waiting were already rejected or harmful.
- Opponent private shed inventory is not observable and must not be used as an input.
- The failed PPO learned broad controls over v18 but did not transfer to the L+ competition result.

Therefore ML should estimate **when the current market is under pressure and which existing priority mode is safer**, while L+ keeps all execution details and can refuse the recommendation.

## Candidate control points

| Rank | ML output | L+ responsibility | Data sufficiency | Recommendation |
|---:|---|---|---|---|
| 1 | Next-clearance market-pressure probability and confidence | Choose among existing sell-priority modes; enforce price, quantity, reserve, and order-count limits | Good for offline feature/label study; 20 full raw replays plus 5,160 sampled rows, with broader telemetry for cohort context | First target |
| 2 | Product priority score for MILK vs STRAWBERRY vs other already-emitted sells | Keep the action set, quantity, affordability, and sanitizer unchanged | Moderate; actions and prices exist, but acceptance and causal effects are not native labels | Second stage |
| 3 | Reinvestment recommendation: preserve cash vs execute an already-valid optional purchase | L+ validates cash, worker, lifecycle, land, and production constraints | Weak-to-moderate; LOSS2POLICY has outcome labels but strong opponent and timing confounding | Defer |
| 4 | Opponent archetype/regime classification from public trajectory signals | Use only as context for ranks 1-2; never inspect private opponent inventory | Moderate for prediction, not causal action attribution | Supporting model |
| 5 | Direct farmer/hand/market action generation | Would bypass the proven engine and safety contract | Not justified | Reject |

## Proposed first model contract

### Inputs

Only information legally available before the decision:

- step, day, hour, clearance position, and remaining horizon;
- current public market prices and market inventory;
- recent price deltas and short rolling trends for MILK, STRAWBERRY, and other sellable products;
- own cash, reserves, shed inventory, production state, workers, plants, pastures, and land count;
- the action L+ would emit before ML intervention: products, quantities, and original order priority;
- public farm/observation fields available to the agent;
- bounded recent market-action summaries derived from observed state transitions.

Do not use opponent private shed inventory, hidden opponent actions before they are observable, replay-only terminal fields, or future prices.

### Outputs

The model returns a small typed object:

```json
{
  "pressure_probability": 0.0,
  "recommended_mode": "LPLUS_DEFAULT",
  "confidence": 0.0,
  "abstain": true
}
```

Initial modes should be a closed set, for example:

- `LPLUS_DEFAULT`: preserve the exact L+ ordering;
- `LPLUS_MILK_PRIORITY`: apply the existing MILK-first rule when its established price gate is satisfied;
- `LPLUS_CONSERVATIVE_PRIORITY`: reorder only already-valid optional sells under a verified pressure condition, without holding required liquidity or changing quantities.

The third mode is an architecture slot, not an implementation decision. It must not be created until an existing trace-derived rule and safe counterfactual are demonstrated.

### Hard safety gate

ML recommendations are ignored when any of the following holds:

- confidence is below a fixed pre-registered threshold;
- the recommendation would create a new order, change quantity, violate the market-order cap, or spend below the L+ reserve;
- the product is not already present in the L+ action;
- the action is outside the known clearance/market timing contract;
- the state is outside the training support or the model is poorly calibrated.

The fallback is always the untouched L+ action.

## Training targets

Use prediction targets before policy targets:

1. **Pressure target:** whether the next observable clearance window produces a materially adverse price movement for a product, defined from the next state transition and pre-registered thresholds.
2. **Opportunity target:** whether the next valid L+ sell opportunity has a favorable realized price relative to the recent product baseline.
3. **Mode target:** an offline ranking label only, based on which existing action priority is associated with better downstream wealth in matched replay contexts. Treat this as a weak label, not causal truth.
4. **Outcome target:** 24-step and 120-step downstream wealth deltas, used for calibration and ranking diagnostics, not as proof that an action caused the outcome.

Do not train on terminal MCV alone. It is too far downstream and mixes opponent strength, market regime, production, and earlier capital decisions.

## Existing data fit

### Usable now

- `data/replay/mcv_replay_dataset.json`: 5,160 sampled records with step, day, cash, inventory, workers, tiles, market prices, executed market action, downstream wealth at 24/120 steps, final wealth, and win label.
- `reports/step5b/old_loss_gauntlet/raw_replays/`: 20 full replay files with 719-step trajectories, actions, observations, public farm state, market prices/inventory, and terminal rewards.
- `reports/live_match_telemetry/`: historical real-match episode populations for cohort and opponent-context analysis.
- Existing phase reports and the research index: prior hypotheses, rejected mechanisms, and regime/failure labels.

### Missing or unsafe as direct labels

- native accepted/rejected/preempted market outcome fields;
- a true intra-step queue position under the official simultaneous clearing semantics;
- counterfactual terminal outcomes for alternate sell priority on the same dynamic state;
- legally observable opponent private inventory;
- a clean, balanced V4.1/L+ action-to-outcome dataset with opponent and seat stratification.

The first model can still be evaluated as a predictor. A causal policy claim requires a later exact-state or paired validation gate and must not be inferred from replay row correlation.

## Offline evaluation plan

1. Build a match-level feature table from cached raw traces only. Preserve all adjacent states needed to verify that each row's baseline action and next observation reproduce exactly.
2. Split by complete match, opponent lineage, and time, never by random rows. Prevent the same replay from appearing in train and validation.
3. Establish a no-ML L+ baseline: default mode, existing ranker behavior, coverage, abstention equivalent, downstream wealth distributions, and tail metrics.
4. Evaluate pressure prediction with calibration, precision/recall by product, lead-time accuracy, and false-positive cost.
5. Evaluate recommendation quality only on states where the model would have acted and where the recommended mode was already legal under L+.
6. Report 24-step and 120-step downstream wealth distributions, win/margin proxies, P05/tail loss, reserve violations, unsupported-state rate, and fallback rate.
7. Require the ML layer to beat or match L+ on every safety metric and improve a pre-registered tail or margin metric before any game is authorized.
8. Only after the offline gate passes, run a small paired, both-seat exact-simulator screen. The frozen L+ artifact remains the baseline and is never edited in place.

## What not to build

- another standalone PPO;
- a model that replaces L+ actions;
- a model trained on private opponent state;
- a model trained from random row splits of replay data;
- a milk-delay rule disguised as ML;
- a land/production optimizer before the market recommendation target survives evaluation;
- a new game run before the environment smoke gate and offline data contract are complete.

## Final recommendation

The smallest defensible L+ + ML experiment is a **public-state market-pressure classifier with abstention**, used only to recommend a narrow sell-priority mode that L+ can accept or reject. It is feasible to prototype offline from the cached data, but the repository does not yet justify training or claiming causal improvement. Keep V4.1/L+ as competition assets and PPO as a frozen research baseline.

