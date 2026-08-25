# L+ ML Downstream Label Audit

Scope: read-only reconstruction from cached complete raw replays. No games or training were run.

Status: **PASS**
Loaded raw replays: **20**
Source rows: **28760**
Rows joined: **28760**

## Reconstruction

The labels use the existing parser rule exactly: `steps[min(719, step + offset)][seat].observation.farms[seat].money`, with offsets 24 and 120. No future prices, terminal MCV, or invented values are used as features.

## Validation

Missing 24-step values: **0**; missing 120-step values: **0**; unmatched rows: **0**.
The historical reduced MCV dataset has zero replay-ID overlap with the 20 current raw trajectories, so the clean join is performed against the full matching raw files.

## Boundary

This proves recoverability of downstream farm-money labels for offline modeling. It does not prove causal market impact, accepted/rejected order outcomes, or that the observed policy is L+.

## Artifacts

- `lplus_market_pressure_dataset_with_downstream.jsonl`
- `LPLUS_ML_DOWNSTREAM_LABEL_AUDIT.json`
- Original dataset preserved unchanged.
