# KAGGRICULTURE CURRENT STATE

**Document Updated**: August 21, 2026  
**Scope**: live production status, verified APEX 4.1 recovery work, and current simulator/CUDA gates.

---

## Latest Verified Update: Step 5B OPT-7

The controlled Step 5B PPO rollout work has progressed beyond the original
OPT-6 batch pilot. The following is the current verified state:

```text
Step 3H CUDA simulator             CLOSED/PAUSED
OPT-1 engine snapshot              PRESERVED
Step 5B smoke/integration          PASS
OPT-6 batch-32 rollout             PROMOTED reference: 0.2177 games/sec total
OPT-7 non-decision feature skip    PROMOTED: 0.3125 games/sec total
Long PPO training                  NOT STARTED
OPT-8 / OPT-9                      NOT STARTED
Production/sealed artifacts        UNTOUCHED
```

OPT-7 was branched from the immutable OPT-6 snapshot and changes only the PPO
rollout path: feature extraction is performed at the validated
`decision_step=120`, while unnecessary non-decision-step extraction is skipped.
The decision feature hash was identical across both matched OPT-7 repetitions.

Verified OPT-7 gate:

```text
32/32 episodes completed             PASS
719 steps per episode                PASS
CUDA device                          cuda:0 / RTX 4050
invalid features / illegal actions  0 / 0
finite PPO losses and gradients      PASS
checkpoint reload                    PASS
total throughput mean                0.3125 games/sec
total throughput std                 0.00575 games/sec
```

Evidence and immutable source snapshot:

```text
reports\step5b\opt7_batch_rep1_report.json
reports\step5b\opt7_batch_rep2_report.json
reports\step5b\source_snapshots\OPT7_SKIP_NONDECISION_FEATURES_0p3125\manifest.json
```

No long PPO training was started. The next work remains explicitly gated and
must not modify Step 3H or sealed production artifacts.

Controlled PPO learning pilot result:

```text
500/500 episodes                  PASS
16 chained PPO update batches     PASS
elapsed                           27.38 minutes
decision_step                     120
CUDA                              cuda:0 / RTX 4050
mean reward range                 0.5814 to 0.6621
win-rate range                    62.5% to 84.4%
first 8 batch mean reward         0.6261
last 8 batch mean reward          0.6248
```

The pilot was numerically and operationally healthy, but the learning curve
showed no clear upward trend. The result is diagnostic only: no PPO checkpoint
was promoted and no long training run was started.

Evidence:

```text
apex_next\ml_engine\training\run_step5b_learning_pilot.py
reports\step5b\learning_pilot_500\pilot_500_summary.json
reports\step5b\learning_pilot_500\batch_00_32ep_report.json through batch_15_20ep_report.json
```

---

## 1. Live Production And Release State

- Active live production agent: `submission.py` remains APEX 3.5 production and frozen.
- Release-ready sealed candidate: `APEX4_SUBMISSION_FINAL.py` remains the approved APEX 4.0 cutover artifact.
- Rollback archive remains preserved under `APEX35_ROLLBACK_ARCHIVE/`.
- Release artifacts remain sealed:
  - `APEX4_PROVENANCE.json`
  - `APEX4_RELEASE_MANIFEST.json`
  - `APEX4_SHA256.txt`
  - `RELEASE_CHECKLIST.md`

Deployment is still locked until explicit human approval. If cutover happens, the action is still byte-identical copy of `APEX4_SUBMISSION_FINAL.py` to `submission.py`.

---

## 2. Historical APEX 4.1 Invalidation

The original APEX 4.1 ML branch was correctly invalidated. That failure history must be preserved.

What was invalidated:

- synthetic `np.random.randn()` training states instead of real observations
- fabricated evaluation metrics instead of measured game outcomes
- non-parity GPU engine behavior
- hardcoded pass validators
- broken `APEX41_*` submission artifacts with invalid action format

This remains true for the original bad branch and for any artifacts tied to it. In particular:

- do not deploy `APEX41_SUBMISSION_FINAL.py`
- do not reuse the invalidated original classifier dataset
- keep `apex_next\ml_engine\INVALIDATED` and `apex_next\ml_engine\data\invalidated\original_seat_bug` as audit evidence

---

## 3. Verified APEX 4.1 Recovery Status

The rebuilt APEX 4.1 work is no longer accurately described as "entire branch dead." The verified state is:

```text
Step 1  environment/features          CLOSED
Step 2  original expert dataset       INVALIDATED for classifier use
Step 3G corrected final dataset       CLOSED
Step 4  opponent classifier           CLOSED
Step 5  PPO smoke mechanics           CLOSED
Step 5A decision timing               CLOSED
Step 5B full PPO                      STOPPED
```

Verified Step 4 / Step 5A facts already present in workspace evidence:

- corrected Step 3G dataset exists and is balanced across 5 archetypes
- opponent classifier checkpoint/report exist under `apex_next\ml_engine`
- Step 5 smoke and timing reports exist under `apex_next\ml_engine\evaluation\step5_strategy`

This does **not** mean APEX 4.1 is deployable. It means the rebuilt pipeline has valid intermediate artifacts, while full PPO training and release integration remain unfinished.

---

## 4. Step 3H Simulator And CUDA Status

Step 3H is the active blocker for fast trustworthy rollouts.

Verified completed gates:

```text
3H-1  initial parity                  PASS
3H-2  market parity                   PASS
3H-3  physical action parity          PASS
3H-4  full single-seed CPU parity     PASS
3H-5  100-seed CPU/vector parity      PASS
3H-6  performance diagnostic          PASS
3H-7  corrected vector port           PASS
3H-7D CPU optimization                PASS
3H-8A CUDA foundation                 PASS
3H-8B physical CUDA tensors           PASS
3H-8C movement/carrying actions       PASS
3H-8D crop actions                    PASS
3H-8E animal actions                  PASS
3H-8F daily crop lifecycle            PASS
3H-8G daily animal lifecycle          PASS
3H-8H full CUDA step ownership        PASS
3H-8I terminal/reward semantics       PASS
3H-8J full single-seed CUDA parity    PASS
3H-8K 20-seed CUDA parity             PASS
```

Current completed gate:

```text
3H-8L 100-seed full CUDA parity       PASS
```

Current promoted optimization:

```text
OPT-1 batched physical synchronization PASS
batch-32 repeated throughput           1.7585 games/sec
batch-32 steps/sec                     1264.37
parity                                 20/20 PASS
```

Evidence for the completed gate:

- 100/100 seeds passed in ten-seed cached-trace chunks
- 71,900 CUDA transitions replayed
- zero first divergences, tensor/object divergences, terminal divergences, or unsupported actions
- CUDA verified on `cuda:0` using the RTX 4050
- no Step 5B rollout or performance benchmark was run

---

## 5. CUDA Freeze And Future Baseline

```text
Historical GOLDEN_0p668 source       ABANDONED / EVIDENCE ONLY
Current corrected CUDA source        FROZEN
NEW_GOLDEN_BASELINE                  ESTABLISHED: 0.688 games/sec
OPT-1 golden baseline                 ESTABLISHED: 1.7585 games/sec @ batch 32
CUDA optimization                    READY FOR NEXT SINGLE OPTIMIZATION
Step 5B PPO                          STOPPED
```

The historical `0.668 games/sec` result remains evidence-only. A separate
Git dangling-object candidate was recovered, validated, and snapshotted as a
new baseline. The current frozen source was not overwritten.

Frozen recovery evidence:

```text
reports\step3h\source_snapshots\corrected_cuda_engine_CURRENT_REGRESSED_20260820.py
reports\step3h\source_snapshots\corrected_cuda_engine_CURRENT_REGRESSED_20260820.json
SHA256: CA54CEACAE86B4AEE5A42E137BD7DEDDD4DA2BA2F8D48E60BA592BBB8C492085
```

The recovery candidate and fresh baseline evidence are:

```text
Git blob: 8b739abda41d25e252fdf04b02d6d73d18186a94
reports\step3h\source_recovery\candidates\corrected_cuda_engine_GIT_CANDIDATE_8b739ab.py
reports\step3h\cuda\RECOVERY_CANDIDATE_8b739AB_20_SEED_PARITY.json
reports\step3h\cuda\RECOVERY_CANDIDATE_8b739AB_BATCH8_BENCHMARK.json
reports\step3h\source_snapshots\corrected_cuda_engine_NEW_GOLDEN_BASELINE_0p688_GIT_8b739ab.py
reports\step3h\source_snapshots\corrected_cuda_engine_NEW_GOLDEN_BASELINE_0p688_GIT_8b739ab.json
SHA256: 6334C614E39B9ACA81AF6A7AF62392E166F192693ECD3BB6AC138ACCF99A94EF
```

Validation:

```text
20/20 cached CUDA parity          PASS
719/719 transitions per seed     PASS
batch-8 fresh benchmark          0.688 games/sec
steps/sec                        494.8
CUDA                             cuda:0 / RTX 4050
PPO                              not run
```

Do not label this new baseline as historical `GOLDEN_0p668`.

OPT-1 promotion evidence:

```text
reports\step3h\cuda\OPT1_BATCH_PHYSICAL_SYNC_20_SEED_PARITY.json
reports\step3h\cuda\OPT1_BATCH_PHYSICAL_SYNC_BATCH32_REPEATED_BENCHMARK.json
reports\step3h\source_snapshots\corrected_cuda_engine_GOLDEN_OPT1_BATCH_PHYSICAL_SYNC_1p7585.py
reports\step3h\source_snapshots\corrected_cuda_engine_GOLDEN_OPT1_BATCH_PHYSICAL_SYNC_1p7585.json
SHA256: 90848D5A29B834CA77251F403616AD31FE4F8AEF18897B39A93500FCB9E6C973
```

## 6. Immutable Snapshot Rule

Before every optimization, snapshot the currently promoted golden source.
Golden snapshots are immutable and must never be overwritten. Each manifest
must record the source hash, runtime/CUDA/GPU details, parent snapshot hash,
parity report, performance report, benchmark parameters, and optimization
stage. Failed candidates are restored from the exact parent snapshot.

Snapshot utility:

```text
apex_next\gpu_engine\snapshot_cuda_engine.py
reports\step3h\source_snapshots
```

Current status summary:

```text
APEX 3.5 live production            FROZEN
APEX 4.0 sealed release candidate   READY
APEX 4.1 rebuilt ML pipeline        PARTIALLY VERIFIED, NOT DEPLOYABLE
3H-8L 100-seed CUDA parity          CLOSED/PASS
Historical source recovery          CLOSED: candidate recovered from Git
New CUDA baseline                    ESTABLISHED: 1.7585 games/sec @ batch 32
CUDA performance benchmark          CLOSED FOR CURRENT GOLDEN
Step 5B PPO                         STOPPED
```
