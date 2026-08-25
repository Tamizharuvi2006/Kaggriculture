# L+ ML Target Validity Audit

Read-only audit. No model was trained and no game was run.

## Decision

**BLOCK_TRAINING_FOR_POLICY_SELECTION**

The 28,760 rows contain one observed trajectory action per state. They do not contain a matched alternative legal action, accepted/rejected/preempted result, queue position, or same-state downstream outcome under another action.

## Findings

Rows: **28760**; matches: **20**; seats: **40**.
Observed action modes: `{'NO_SELL': 19894, 'OTHER_FIRST': 4902, 'WOOL_FIRST': 982, 'MILK_FIRST': 1389, 'STRAWBERRY_FIRST': 1593}`.
Exact same-state groups with competing actions: **0**.
Quantized public-state repeats with action variation: **4**, which is only approximate matching and is not causal evidence.

## Target Assessment

- Adverse/favorable price labels are valid descriptive future outcomes, not action targets.
- 24-step/120-step farm-money labels are valid downstream outcomes, not causal incremental action effects.
- The observed mode label is behavior copied from a replay, not a proven optimal label.
- A loss replay identifies a failed trajectory, not the correct opposite action.

## Missing Evidence

- accepted/rejected/preempted market outcome
- order or queue position
- legal competing action at the same state
- matched counterfactual result
- opponent private state/action causal decomposition

## Recommendation

Do not train or integrate a policy from this dataset. A descriptive market-risk predictor could be studied separately, but it must not be interpreted as an action recommendation without matched intervention evidence. Preserve original L+ as the fallback.
