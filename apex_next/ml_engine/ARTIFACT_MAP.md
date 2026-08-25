# APEX 4.1 ML Artifact Map

This folder contains APEX 4.1 Hybrid ML code and artifacts. The live Kaggle
execution files remain outside this layout and must stay sealed unless a release
gate explicitly approves integration.

## Current Canonical Data

- `data/current/step3g_targeted_1000/`
  - Final corrected 1,000-game dataset.
  - Balanced five-archetype labels.
  - Use this for Step 4+ training and evaluation.

## Validation And Pilots

- `data/validation/step3g_targeted_validation_100/`
  - Corrected 100-game validation data before the final Step 3G run.
- `data/pilots/step2_pilot/`
  - Original Step 2 pilot outputs.
- `data/pilots/step3e_replacement/`
  - Corrected telemetry replacement pilots.
- `data/pilots/step3f_targeted/`
  - Targeted archetype pilot outputs.

## Invalidated Data

- `data/invalidated/original_seat_bug/`
  - Original 1,000-game classifier dataset collected before the seat-1 opponent
    adapter bug was fixed.
  - Keep for audit only. Do not train classifier or PPO components from it.

## Reports

- `evaluation/step1_environment/`
  - Step 1 environment and feature acceptance reports.
- `evaluation/step3_diagnostics/`
  - Label diagnostics, seat-bug probes, adapter reports, and targeted pilot
    audits.
- `evaluation/step4_classifier/`
  - Opponent classifier evaluation reports.
- `evaluation/step5_strategy/`
  - Strategy selector smoke, timing, and benchmark reports.

## Checkpoints

- `checkpoints/opponent_classifier/`
  - Validated Step 4 classifier checkpoint.
- `checkpoints/strategy_selector/`
  - Step 5 smoke and timing selector checkpoints.
- `checkpoints/benchmarks/`
  - Temporary Step 5B benchmark checkpoints. Do not treat as final policies.

## Quick Verification

Run:

```powershell
python apex_next\ml_engine\verify_artifact_layout.py
```

The verifier checks the current dataset, labels, reports, checkpoints, and
invalidated-dataset marker without starting training.
