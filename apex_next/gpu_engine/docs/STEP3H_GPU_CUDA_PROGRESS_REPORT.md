# Step 3H GPU/CUDA Progress Report

Date: 2026-08-21

Scope: APEX 4.1 Hybrid ML simulator acceleration work for Kaggriculture.

This report summarizes the work completed so far, the exact evidence available,
and the next safe gates. It is intentionally separate from sealed production
artifacts.

## Executive Summary

### Latest Step 5B Handoff

Step 3H remains closed and paused. The validated OPT-1 engine is now being
used by the Step 5B PPO adapter. A controlled batch-rollout optimization,
OPT-7, was promoted after formal functional checks and repeated benchmarking.

```text
OPT-6 batch-32 reference          0.2177 games/sec total
OPT-7 feature skip                0.3125 games/sec total
OPT-7 improvement                 approximately 43.8%
OPT-7 episodes                    32/32 complete
OPT-7 steps                      719 per episode
decision_step                    120
CUDA                             cuda:0 / RTX 4050
long PPO training                not started
```

OPT-7 skips feature extraction on non-decision steps while preserving the
validated decision-step features and PPO semantics. Its immutable snapshot and
manifest are stored at:

`D:\Kaggriculture\reports\step5b\source_snapshots\OPT7_SKIP_NONDECISION_FEATURES_0p3125\manifest.json`

Reports:

```text
D:\Kaggriculture\reports\step5b\opt7_batch_rep1_report.json
D:\Kaggriculture\reports\step5b\opt7_batch_rep2_report.json
```

Do not start OPT-8/OPT-9 or long PPO training automatically. Do not modify
the Step 3H snapshot or sealed production files.

The subsequent 500-episode controlled PPO learning pilot completed separately
from Step 3H. It used 16 chained CUDA PPO batches, completed all 500 episodes
in 27.38 minutes, and passed operational checks. The reward curve was flat
(first-half mean 0.6261 versus second-half mean 0.6248), so no checkpoint was
promoted and long training remains paused.

The project moved from a suspicious "GPU engine" folder to a parity-tested CUDA
simulator path.

Current status:

```text
3H-1  Initial state parity              PASS
3H-2  Market transition parity          PASS
3H-3  Physical action parity            PASS
3H-4  Full single-seed CPU parity       PASS
3H-5  100-seed CPU/vector parity        PASS
3H-6  Performance diagnostic            PASS
3H-7  Corrected vector port             PASS
3H-7D CPU optimization                  PASS
3H-8A CUDA foundation                   PASS
3H-8B Physical CUDA tensors             PASS
3H-8C Movement/carrying actions         PASS
3H-8D Crop actions                      PASS
3H-8E Animal actions                    PASS
3H-8F Daily crop lifecycle              PASS
3H-8G Daily animal lifecycle            PASS
3H-8H Full CUDA step ownership          PASS
3H-8I Terminal/reward semantics         PASS
3H-8J Full single-seed CUDA trajectory  PASS
3H-8K 20-seed full CUDA parity          PASS

3H-8L 100-seed full CUDA parity         CLOSED/PASS
3H-8M CUDA performance benchmark        PASS: new baseline 0.688 games/sec
Step 5B PPO                             STOPPED
```

The current CUDA engine is not being accepted because it is "fast" yet. It is
being accepted gate by gate because it matches the parity-correct CPU reference
and real Kaggriculture action traces.

## What Was Built

### Correctness Reference

`D:\Kaggriculture\apex_next\gpu_engine\paired_sim_v2.py`

Purpose:

- Acts as the exact replay/reference simulator derived from real Kaggriculture.
- Used to discover and validate reset, market, physical, crop, animal, terminal,
  and reward semantics.

### Corrected CPU Vector Engine

`D:\Kaggriculture\apex_next\gpu_engine\paired_gpu_v25\corrected_vector_engine.py`

Purpose:

- Ports the validated PairedSimV2 semantics into a batch/vector architecture.
- Passed 100-seed full trajectory parity.
- Current validated CPU baseline:

```text
100/100 parity          PASS
performance baseline    13.76 games/sec
steps/sec               9,890 approx
backend                 NumPy CPU
CUDA                    false
```

### Corrected CUDA Engine

`D:\Kaggriculture\apex_next\gpu_engine\paired_gpu_v25\corrected_cuda_engine.py`

Purpose:

- CUDA-resident numeric/tensor implementation of the corrected vector engine.
- Uses PyTorch CUDA tensors on the RTX 4050.
- Passed full 20-seed CUDA trajectory parity.

Important implementation changes:

- Added terminal/reward metrics matching the corrected CPU reference.
- Fixed stale day-boundary tensor mirror synchronization.
- Added deferred physical tensor synchronization inside `step_integrated` to
  avoid repeated tiny CUDA writes during each integrated transition.

### Multi-Seed CUDA Parity Harness

`D:\Kaggriculture\apex_next\gpu_engine\step3h8k_multiseed_cuda_parity.py`

Purpose:

- Reuses cached real Kaggriculture action traces.
- Replays identical traces through CPU and CUDA engines.
- Compares numeric state, object state, tensor mirrors, terminal state, reward,
  unsupported actions, and CUDA device usage.

This harness exists because regenerating real Kaggriculture traces for every
CUDA validation run was too slow and unnecessary.

### Hot-Path Profiler

`D:\Kaggriculture\apex_next\gpu_engine\profile_step3h8k_replay_hotpath.py`

Purpose:

- Separates replay timing into CPU step, CUDA step, CUDA sync, numeric compare,
  object compare, and tensor compare.
- Confirmed the old bottleneck was `gpu.step_integrated`, not trace loading or
  JSON reporting.

## Key Findings

### Finding 1: The Old Fast V25 Engine Was Not Trustworthy

The older V25 vector engine could report very high throughput, but it did not
contain all parity-correct mechanics. It was useful as a speed reference only,
not as a training substrate.

### Finding 2: Correctness Had To Come Before CUDA

The project first established:

```text
Real Kaggriculture
        -> PairedSimV2
        -> Corrected CPU vector engine
        -> Corrected CUDA engine
```

This prevented the old failure mode:

```text
fast simulator
        -> wrong semantics
        -> fake ML evidence
```

### Finding 3: Reusing Real Action Traces Is Required

The 3H-8K architecture now uses cached real traces:

```text
cached real Kaggriculture action trace
        -> CPU reference replay
        -> CUDA replay
        -> compare
```

This keeps real Kaggriculture as the truth source without paying the real
environment cost every time a CUDA parity gate runs.

Trace cache:

`D:\Kaggriculture\reports\step3h\traces\step3h_real_action_traces`

Current cached seeds:

```text
39000 through 39019
20 trace files
719 actions/transitions each
```

### Finding 4: The Main CUDA Bottleneck Was Repeated Physical Tensor Sync

Before deferred sync:

```text
2-seed full CUDA parity      318.66 sec
```

After deferred sync:

```text
2-seed full CUDA parity       28.19 sec
```

Profiler evidence:

```text
Before:
gpu_step_integrated  6.717 sec / 24-step probe

After:
gpu_step_integrated  0.895 sec / 24-step probe
```

This was a validation-safe optimization: the object semantics do not change;
the tensor mirrors are flushed to the same end-of-step state.

## Current Best Evidence

### 3H-8J Post-Optimization Single-Seed Audit

Report:

`D:\Kaggriculture\reports\step3h\cuda\STEP3H8J_FULL_CUDA_TRAJECTORY_AUDIT_POST_DEFERRED_SYNC.json`

Result:

```text
status                    PASS
seed                      39000
real transitions           719
CPU transitions            719
CUDA transitions           719
first divergence           null
tensor/object divergence   null
terminal divergence        null
unsupported actions        0
CUDA                       true
device                     cuda:0
GPU                        NVIDIA GeForce RTX 4050 Laptop GPU
wall time                  16.153832 sec
```

### 3H-8K 20-Seed Full CUDA Parity

Report:

`D:\Kaggriculture\reports\step3h\cuda\STEP3H8K_20_SEED_CUDA_PARITY.json`

Result:

```text
status                    PASS
seeds tested              20
seeds passed              20
seeds failed              0
pass rate                 1.0
real transitions/seed      719
CPU transitions/seed       719
CUDA transitions/seed      719
first divergence           null for all seeds
tensor/object divergence   null for all seeds
terminal divergence        null for all seeds
unsupported actions        0 for all seeds
CUDA                       true
tensor device              cuda:0
GPU                        NVIDIA GeForce RTX 4050 Laptop GPU
```

Timing:

```text
trace load/create          46.932805 sec
batched CPU/CUDA replay   263.204942 sec
terminal finalize           0.053703 sec
total wall                311.323 sec
```

Trace source:

```text
cached traces              2
created this run           18
```

The next run over these same 20 seeds should skip that one-time trace creation
cost.

## Files Added Or Changed In This CUDA Phase

New or changed code:

```text
D:\Kaggriculture\apex_next\gpu_engine\paired_gpu_v25\corrected_cuda_engine.py
D:\Kaggriculture\apex_next\gpu_engine\step3h8j_full_cuda_trajectory_audit.py
D:\Kaggriculture\apex_next\gpu_engine\step3h8k_multiseed_cuda_parity.py
D:\Kaggriculture\apex_next\gpu_engine\profile_step3h8k_replay_hotpath.py
```

New or important reports:

```text
D:\Kaggriculture\reports\step3h\cuda\STEP3H8J_FULL_CUDA_TRAJECTORY_AUDIT_POST_DEFERRED_SYNC.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8K_2_SEED_CUDA_PARITY_DEFERRED_SYNC.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8K_20_SEED_CUDA_PARITY.json
D:\Kaggriculture\reports\step3h\profiles\STEP3H8K_HOTPATH_PROFILE_2SEED_24STEP.json
D:\Kaggriculture\reports\step3h\profiles\STEP3H8K_HOTPATH_PROFILE_2SEED_24STEP_DEFERRED_SYNC.json
```

Trace cache:

```text
D:\Kaggriculture\reports\step3h\traces\step3h_real_action_traces\
```

## Boundaries Preserved

Untouched intentionally:

```text
D:\Kaggriculture\submission.py
D:\Kaggriculture\APEX4_SUBMISSION_FINAL.py
sealed production artifacts
invalidated old ML pipeline
```

Training status:

```text
Step 5B PPO                stopped
Step 6 Market Timer        not started
CUDA performance benchmark not started
Kaggle packaging           not touched
```

## Current Decision

3H-8L is closed/pass based on the cached 100-seed parity evidence. However,
the current `corrected_cuda_engine.py` still fails its fresh parity check at
step 351 on `plant_tiles` and remains frozen. A separate Git dangling-object
candidate was recovered and passed the required cached parity and batch-8
benchmark. The historical `0.668 games/sec` report remains evidence-only.

Current source-control state:

```text
current engine                  FROZEN / NOT OVERWRITTEN
historical GOLDEN_0p668 source  ABANDONED / EVIDENCE ONLY
new golden baseline             1.7585 games/sec @ batch 32 (OPT-1)
CUDA optimization              READY FOR NEXT SINGLE OPTIMIZATION
Step 5B PPO                    STOPPED
```

Recovery and baseline evidence:

```text
Git blob 8b739ab...
        -> cached 20-seed parity PASS
        -> batch-8 benchmark 0.688 games/sec
        -> immutable NEW_GOLDEN_BASELINE snapshot
```

Snapshot:

```text
D:\Kaggriculture\reports\step3h\source_snapshots\corrected_cuda_engine_NEW_GOLDEN_BASELINE_0p688_GIT_8b739ab.py
D:\Kaggriculture\reports\step3h\source_snapshots\corrected_cuda_engine_NEW_GOLDEN_BASELINE_0p688_GIT_8b739ab.json
```

Do not relabel this baseline as historical `GOLDEN_0p668`.

OPT-1 batched physical synchronization promotion:

```text
20-seed cached CUDA parity       PASS (20/20, 719/719 each)
Repeated batch-32 benchmark      1.7585 games/sec mean
Benchmark standard deviation     0.0104 games/sec
Mean steps/sec                   1264.37
CUDA                             cuda:0 / RTX 4050
PPO                              not run
Snapshot SHA256                  90848D5A29B834CA77251F403616AD31FE4F8AEF18897B39A93500FCB9E6C973
```

Evidence:

```text
D:\Kaggriculture\reports\step3h\cuda\OPT1_BATCH_PHYSICAL_SYNC_20_SEED_PARITY.json
D:\Kaggriculture\reports\step3h\cuda\OPT1_BATCH_PHYSICAL_SYNC_BATCH32_REPEATED_BENCHMARK.json
D:\Kaggriculture\reports\step3h\source_snapshots\corrected_cuda_engine_GOLDEN_OPT1_BATCH_PHYSICAL_SYNC_1p7585.py
D:\Kaggriculture\reports\step3h\source_snapshots\corrected_cuda_engine_GOLDEN_OPT1_BATCH_PHYSICAL_SYNC_1p7585.json
```

Snapshot utility:

```text
D:\Kaggriculture\apex_next\gpu_engine\snapshot_cuda_engine.py
D:\Kaggriculture\reports\step3h\source_snapshots
```

Every promoted implementation must have an immutable source file and manifest
containing SHA256, runtime/CUDA/GPU, parent snapshot, parity evidence, and
performance evidence. Golden snapshots must never be overwritten.

## Open Question

The only open organization question is whether to physically move historical
raw JSON reports into subfolders. I recommend not doing that until we update
script defaults, because current audit scripts read and write under
`D:\Kaggriculture\reports`.
