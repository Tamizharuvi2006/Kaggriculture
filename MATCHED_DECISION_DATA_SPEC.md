# Matched Decision Data Specification

Status: **DESIGN ONLY**

This document defines the minimum evidence required before training a decision-making ML model. It does not authorize game runs, model training, L+/V4.1 changes, or production integration.

## Atomic Evidence Unit

One record is a matched decision set:

```text
match / lineage
  decision point t
    canonical state S
      legal actions {A, B, ...}
    branch S + A -> execution and downstream outcomes
    branch S + B -> execution and downstream outcomes
```

An isolated `(state, action, reward)` row is insufficient for causal action learning.

## Required State Identity

Every branch must reference the same serialized simulator state artifact, with:

- canonical state hash
- simulator and engine version
- episode seed and branch seed policy
- match, seat, decision step, and lineage identifiers
- complete public state
- acting player's private state when legally available to the policy
- market state and pending orders
- cash, inventory, workers, land, production, and lifecycle state
- RNG state or an equivalent deterministic replay token

State equality must be verified by byte-stable serialization or a documented canonical hash. Similar observations do not qualify as exact-state matches.

## Legal Action Verification

At state `S`, record:

- the complete legal-action mask or enumerated legal action set
- the action schema and simulator validation result
- each selected branch action exactly as submitted
- rejected/invalid action details, if any

Only actions present in the legal set may be compared. A failed action is not a valid counterfactual branch.

## Branch Controls

For every branch:

- fork from the same immutable state snapshot
- use controlled and recorded RNG behavior
- record whether randomness is identical, coupled, or independently sampled
- preserve all non-intervention actions and configuration
- record the first divergence from the canonical state
- verify replay parity before accepting outcomes

If the simulator cannot hold all non-intervention factors constant, the record must mark the comparison as non-identifying and exclude it from the causal training gate.

## Required Outcomes

Each legal branch must capture:

### Immediate execution

- accepted/rejected/preempted status
- executed quantity and price
- queue/order position when applicable
- cash before/after
- inventory before/after
- market state before/after clearance
- opponent public market activity

### Downstream windows

- 24-step state snapshot and wealth/MCV metrics
- 120-step state snapshot and wealth/MCV metrics
- terminal outcome where the branch is run to completion
- intervention metadata identifying the changed action only

Missing outcomes make the matched set incomplete; they must not be imputed.

## Dataset Lineage And Splits

Each matched set receives:

- `lineage_id`
- `source_match_id`
- `seed_id`
- `seat`
- `opponent_regime_id`
- `decision_step`
- `parent_state_hash`
- branch IDs and action hashes

Train/validation/test partitions must be assigned by complete lineage or episode family. All branches from one parent state and all nearby decision points from that episode stay in one partition.

Coverage must be reported across seeds, seats, opponent regimes, products, decision horizons, and action pairs.

## Collector Validation Protocol

Before collecting a full dataset, validate a small controlled sample:

1. Serialize one canonical state and verify stable hash reproduction.
2. Fork at least two legal actions from that exact state.
3. Confirm both branches pass simulator legality checks.
4. Confirm non-intervention state is identical immediately before the action.
5. Confirm the first divergence is the selected action.
6. Confirm execution and market outcomes are captured.
7. Confirm 24-step and 120-step snapshots are present and replayable.
8. Repeat under at least two seeds and both seats.
9. Re-run one branch and verify deterministic parity or quantify controlled variance.
10. Preserve raw branch artifacts and a machine-readable validation report.

The collector is not approved for full data generation until every check passes.

## Acceptance Gate

```text
MATCHED DATASET PASS
├── Same-state branch identity verified
├── At least two legal actions per decision
├── Execution outcome captured
├── 24-step outcome captured
├── 120-step outcome captured
├── Market acceptance/rejection/queue captured where applicable
├── Coverage across seeds
├── Coverage across seats
├── Coverage across opponent regimes
├── No cross-lineage leakage
└── Replay/parity audit passed
```

Until this gate passes, ML may only perform descriptive analysis. It may not select actions, alter L+, or replace V4.1 behavior.
