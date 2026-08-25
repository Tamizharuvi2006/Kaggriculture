# Kaggriculture Project Map

**Document Updated**: August 21, 2026

This is the quick navigation file for `D:\Kaggriculture`.

## Start Here

```text
README.md
KAGGRICULTURE_CURRENT_STATE.md
TODO.md
BASELINE_CONTRACT.md
KAGGRICULTURE_FOLDER_ORGANIZATION_REPORT.md
```

## Do Not Touch Without Explicit Approval

```text
submission.py
APEX4_SUBMISSION_FINAL.py
APEX41_SUBMISSION_FINAL.py
APEX4_PROVENANCE.json
APEX4_RELEASE_MANIFEST.json
APEX4_SHA256.txt
BASELINE_CONTRACT.md
RELEASE_CHECKLIST.md
apex_next\ml_engine\INVALIDATED
reports\step3h\traces\step3h_real_action_traces
```

## Current Active Work Areas

### APEX 4.1 Hybrid ML

```text
apex_next\ml_engine
```

Docs:

```text
apex_next\ml_engine\ARTIFACT_MAP.md
```

Current artifact layout:

```text
apex_next\ml_engine\data\current\step3g_targeted_1000
apex_next\ml_engine\data\invalidated\original_seat_bug
apex_next\ml_engine\evaluation\step4_classifier
apex_next\ml_engine\evaluation\step5_strategy
apex_next\ml_engine\checkpoints\opponent_classifier
apex_next\ml_engine\checkpoints\strategy_selector
```

Status:

```text
Step 1 environment/features       CLOSED
Step 3G corrected dataset         CLOSED
Step 4 classifier                 CLOSED
Step 5 smoke/timing               CLOSED
Step 5A decision timing           CLOSED
Step 5B PPO infrastructure         CLOSED/PASS
Step 5B OPT-6 batch rollout        PROMOTED: 0.2177 games/sec total
Step 5B OPT-7 feature skip         PROMOTED: 0.3125 games/sec total
Step 5B 500-episode learning pilot COMPLETED: diagnostic only
Step 5B long PPO training          NOT STARTED
```

### Step 3H Simulator/CUDA

```text
apex_next\gpu_engine
```

Docs:

```text
apex_next\gpu_engine\docs\README.md
```

Status:

```text
3H-8K 20-seed CUDA parity         CLOSED/PASS
3H-8L 100-seed CUDA parity        CLOSED/PASS
Historical GOLDEN_0p668 source    ABANDONED / EVIDENCE ONLY
Current CUDA source               FROZEN
Historical recovery               CLOSED
New CUDA baseline                 ESTABLISHED: 1.7585 games/sec @ batch 32 (OPT-1)
CUDA performance benchmark       CLOSED FOR CURRENT GOLDEN
Step 5B PPO                       STOPPED
```

Source recovery and snapshot control:

```text
apex_next\gpu_engine\snapshot_cuda_engine.py
reports\step3h\source_snapshots
reports\step3h\source_recovery
```

The historical `0.668 games/sec` report remains evidence only. A separate Git
dangling-object candidate (`8b739ab...`) passed cached 20-seed parity and a
fresh batch-8 benchmark at `0.688 games/sec`. It is snapshotted separately as
`NEW_GOLDEN_BASELINE_0p688_GIT_8b739ab`; the frozen current source was not
overwritten.

OPT-1 batched physical synchronization passed cached 20-seed parity and three
repeated batch-32 benchmark runs, improving the stable reference from 1.1726
to 1.7585 games/sec. Its immutable snapshot and evidence are recorded under
`reports\step3h\source_snapshots` and `reports\step3h\cuda`.

Every future promoted optimization requires an immutable source snapshot,
SHA256, runtime manifest, parent snapshot, parity evidence, and performance
evidence. Failed candidates must be restored from the parent snapshot.

Latest Step 5B evidence:

```text
reports\step5b\opt7_batch_rep1_report.json
reports\step5b\opt7_batch_rep2_report.json
reports\step5b\source_snapshots\OPT7_SKIP_NONDECISION_FEATURES_0p3125\manifest.json
```

OPT-7 passed 32/32 episodes at 719 steps each, preserved decision timing at
step 120, used CUDA `cuda:0`, and reduced feature extraction to the decision
step. No long PPO training, OPT-8/OPT-9, or production integration has begun.

The 500-episode learning pilot completed in 27.38 minutes using 16 chained
CUDA batch updates. It passed all operational checks, but reward and win-rate
did not show a clear upward trend, so its checkpoint was not promoted.
Evidence is under `reports\step5b\learning_pilot_500`.

### APEX 4 Research/Lab

```text
apex_next\apex4
apex_next\lab
apex_next\research
research
research_results
```

These contain older and current research machinery. Do not assume a report here
is current without checking timestamps and `KAGGRICULTURE_CURRENT_STATE.md`.

## Raw Evidence

```text
reports
```

This is the main messy folder. Important current subfolder:

```text
reports\step3h\traces\step3h_real_action_traces
```

Important current CUDA report:

```text
reports\step3h\cuda\STEP3H8K_20_SEED_CUDA_PARITY.json
```

Completed 3H-8L evidence:

```text
- 100/100 seeds passed in ten-seed cached-trace chunks
- 71,900 CUDA transitions replayed
- zero divergences, unsupported actions, and exceptions
- RTX 4050 execution confirmed on `cuda:0`
- Step 5B remains stopped
```

## Historical / Candidate Areas

```text
apex
baseline
benchmarks
competitive_intelligence
experiments
generalization_pipeline
l+reviews
l++reviews
scratch
docs
```

These need cleanup, but should be archived only after confirming whether any
current scripts still import/read from them.

## Recommended Next Cleanup Step

Current Step 3H evidence has already been migrated into:

```text
reports\step3h\parity
reports\step3h\vector
reports\step3h\cuda
reports\step3h\profiles
reports\step3h\traces
reports\step3h\seed_reports
```

ML artifacts have now been organized in-place inside `apex_next\ml_engine`.

Root data artifacts now live in:

```text
data\replay\mcv_replay_dataset.json
data\replay\manifest.csv
data\logs\episode-90744327-agent-0-logs.json
data\notebooks\what-actually-wins-on-the-kaggriculture-ladder.ipynb
```

Next cleanup step: sort historical top-level research/release JSON reports only
after checking whether current scripts still reference them.
