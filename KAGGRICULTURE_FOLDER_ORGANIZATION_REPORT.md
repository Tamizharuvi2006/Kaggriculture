# Kaggriculture Folder Organization Report

Date: 2026-08-18

Scope: full `D:\Kaggriculture` workspace.

This began as an audit, then the approved safe cleanup was applied for Step 3H
reports and APEX 4.1 ML artifacts. No files were deleted, and sealed/live
production artifacts were not moved.

## Current Problem

The workspace has several different kinds of material mixed together:

- sealed/live submissions
- APEX 4.0 and APEX 4.1 release artifacts
- APEX 4.1 Hybrid ML pipeline files
- Step 3H simulator/CUDA parity work
- historical research reports
- generated JSON evidence
- old experiments and scratch material
- Python caches

Because these are mixed at the root and under `reports`, it is hard to tell
which file is the current source of truth.

## Top-Level Folder Audit

```text
D:\Kaggriculture
```

Current top-level directories:

```text
__pycache__                    Python cache; generated.
.git                           Git metadata; never manually edit.
.pytest_cache                  Test cache; generated.
apex                           Older APEX code area.
apex_next                      Current active APEX-next workspace.
APEX35_ROLLBACK_ARCHIVE        APEX 3.5 rollback/archive material.
baseline                       Baseline contracts/archive material.
benchmarks                     Older benchmark scripts/results.
competitive_intelligence       Competitive intelligence research.
data                           Organized replay/log/notebook data artifacts.
docs                           Historical research documentation.
experiments                    Experiment folders.
generalization_pipeline        Generalization candidate/pipeline work.
l++reviews                     Review artifacts.
l+reviews                      Review artifacts.
reports                        Main raw evidence/report dump.
research                       Research scripts.
research_results               Research result artifacts.
scratch                        Scratch/temp experiments.
```

Current top-level files:

```text
.gitignore
APEX4_PROVENANCE.json
APEX4_RELEASE_MANIFEST.json
APEX4_SHA256.txt
APEX4_SUBMISSION_FINAL.py
APEX41_SUBMISSION_FINAL.py
BASELINE_CONTRACT.md
DATA_INDEX.md
KAGGLE_RATING_TIMELINE_RECONSTRUCTION.md
KAGGRICULTURE_CURRENT_STATE.md
README.md
RELEASE_CHECKLIST.md
requirements.txt
submission.py
TODO.md
```

## What Is Current Truth

### Production/live/sealed artifacts

Do not move or modify without explicit release-flow work:

```text
D:\Kaggriculture\submission.py
D:\Kaggriculture\APEX4_SUBMISSION_FINAL.py
D:\Kaggriculture\APEX4_PROVENANCE.json
D:\Kaggriculture\APEX4_RELEASE_MANIFEST.json
D:\Kaggriculture\APEX4_SHA256.txt
D:\Kaggriculture\BASELINE_CONTRACT.md
D:\Kaggriculture\RELEASE_CHECKLIST.md
```

### Current active development

```text
D:\Kaggriculture\apex_next
```

Important subfolders:

```text
apex_next\apex4       APEX 4 system/research/candidate code.
apex_next\gpu_engine  Step 3H simulator/vector/CUDA work.
apex_next\lab         research/release lab framework.
apex_next\ml_engine   APEX 4.1 Hybrid ML pipeline.
apex_next\research    newer research scripts.
```

### Current ML pipeline

```text
D:\Kaggriculture\apex_next\ml_engine
```

Important subfolders:

```text
checkpoints     trained/smoke model checkpoints.
data            current data artifacts.
datasets        dataset helpers/artifacts.
evaluation      evaluation reports.
INVALIDATED     invalidated old/bad datasets or pipelines.
models          model definitions.
tests           ML tests.
training        training scripts.
```

### Current simulator/CUDA work

```text
D:\Kaggriculture\apex_next\gpu_engine
```

Human-readable docs now start at:

```text
D:\Kaggriculture\apex_next\gpu_engine\docs\README.md
```

Current CUDA checkpoint:

```text
3H-8K 20-seed full CUDA trajectory parity: PASS
```

Next CUDA checkpoint:

```text
3H-8L 100-seed full CUDA trajectory parity
```

## Applied Cleanup

### Step 3H evidence

Step 3H simulator/vector/CUDA evidence was moved out of the flat `reports`
folder into:

```text
D:\Kaggriculture\reports\step3h\parity
D:\Kaggriculture\reports\step3h\vector
D:\Kaggriculture\reports\step3h\cuda
D:\Kaggriculture\reports\step3h\profiles
D:\Kaggriculture\reports\step3h\traces
D:\Kaggriculture\reports\step3h\seed_reports
```

Step 3H scripts were patched to write new reports into those folders. A
one-seed 3H-8K layout verification replay passed using the relocated cached
trace.

### APEX 4.1 ML artifacts

ML data, reports, and checkpoints were moved from flat folders into:

```text
D:\Kaggriculture\apex_next\ml_engine\data\current\step3g_targeted_1000
D:\Kaggriculture\apex_next\ml_engine\data\validation\step3g_targeted_validation_100
D:\Kaggriculture\apex_next\ml_engine\data\pilots
D:\Kaggriculture\apex_next\ml_engine\data\benchmarks
D:\Kaggriculture\apex_next\ml_engine\data\invalidated\original_seat_bug
D:\Kaggriculture\apex_next\ml_engine\evaluation\step1_environment
D:\Kaggriculture\apex_next\ml_engine\evaluation\step3_diagnostics
D:\Kaggriculture\apex_next\ml_engine\evaluation\step4_classifier
D:\Kaggriculture\apex_next\ml_engine\evaluation\step5_strategy
D:\Kaggriculture\apex_next\ml_engine\checkpoints\opponent_classifier
D:\Kaggriculture\apex_next\ml_engine\checkpoints\strategy_selector
D:\Kaggriculture\apex_next\ml_engine\checkpoints\benchmarks
```

ML scripts were patched to use the new default paths. The old seat-adapter-bug
dataset is retained only under `data\invalidated\original_seat_bug`.

### Root data artifacts

Replay, log, manifest, and notebook artifacts were moved out of the workspace
root into:

```text
D:\Kaggriculture\data\replay\mcv_replay_dataset.json
D:\Kaggriculture\data\replay\manifest.csv
D:\Kaggriculture\data\logs\episode-90744327-agent-0-logs.json
D:\Kaggriculture\data\notebooks\what-actually-wins-on-the-kaggriculture-ladder.ipynb
```

Known Python readers/writers were patched to use the new `data\replay` and
`data\notebooks` paths.

## Reports Folder Problem

```text
D:\Kaggriculture\reports
```

This folder currently contains hundreds of mixed reports.

Approximate report groups:

```text
APEX4       42
APEX41      many current/historical APEX 4.1 reports
EXP         103
PHASE       46
RESEARCH    22
STEP3H      43
OTHER       134
```

Current important report subfolders:

```text
reports\live_match_telemetry
reports\step3h\traces\step3h_real_action_traces
reports\step3h\seed_reports\step3h8k_seed_reports
```

Main issue:

```text
reports
    contains live release reports,
    old phase reports,
    experiment reports,
    Step 3H simulator evidence,
    ML stage evidence,
    forensic reports,
    and scratch/probe outputs all together.
```

## Recommended Target Layout

Do not apply this blindly. This is the clean target after script paths are
updated and verified.

```text
D:\Kaggriculture
│
├── README.md
├── KAGGRICULTURE_CURRENT_STATE.md
├── TODO.md
├── BASELINE_CONTRACT.md
├── RELEASE_CHECKLIST.md
│
├── sealed\
│   ├── apex4\
│   │   ├── APEX4_SUBMISSION_FINAL.py
│   │   ├── APEX4_PROVENANCE.json
│   │   ├── APEX4_RELEASE_MANIFEST.json
│   │   └── APEX4_SHA256.txt
│   └── apex35\
│       └── APEX35_ROLLBACK_ARCHIVE\
│
├── live\
│   └── submission.py
│
├── apex_next\
│   ├── apex4\
│   ├── gpu_engine\
│   ├── lab\
│   ├── ml_engine\
│   └── research\
│
├── data\
│   ├── replay\
│   │   └── mcv_replay_dataset.json
│   ├── notebooks\
│   │   └── what-actually-wins-on-the-kaggriculture-ladder.ipynb
│   └── logs\
│       └── episode-90744327-agent-0-logs.json
│
├── reports\
│   ├── release\
│   ├── ml\
│   ├── step3h\
│   │   ├── parity\
│   │   ├── cuda\
│   │   ├── profiles\
│   │   └── traces\
│   ├── experiments\
│   ├── phases\
│   └── research\
│
├── archive\
│   ├── old_apex\
│   ├── old_reviews\
│   ├── old_benchmarks\
│   └── scratch\
│
└── docs\
    ├── research_history\
    ├── architecture\
    └── operations\
```

## Safe Cleanup Rules

Before moving anything:

1. Freeze the current state in a report.
2. Update scripts to use new report paths.
3. Keep backward-compatible reads for old paths.
4. Move one small category first, such as Step 3H reports.
5. Run the audit that depends on those files.
6. Only then migrate the next category.

Never move/delete without explicit approval:

```text
submission.py
APEX4_SUBMISSION_FINAL.py
APEX41_SUBMISSION_FINAL.py
BASELINE_CONTRACT.md
RELEASE_CHECKLIST.md
APEX4 provenance/hash/manifest files
apex_next\ml_engine\INVALIDATED
reports\step3h\traces\step3h_real_action_traces
```

## Recommended Immediate Fix

Completed first cleanup:

```text
KAGGRICULTURE_PROJECT_MAP.md
KAGGRICULTURE_FOLDER_ORGANIZATION_REPORT.md
reports\step3h\parity
reports\step3h\vector
reports\step3h\cuda
reports\step3h\profiles
reports\step3h\traces
reports\step3h\seed_reports
```

Step 3H scripts were updated to write to the new folders. A 1-seed CUDA
layout-verification audit passed after migration.

Recommended next cleanup:

```text
apex_next\ml_engine evaluation/checkpoint/data reports
```

Do not move sealed/live files.

## Current Open Questions

1. Should sealed files stay at root for compatibility, or move under `sealed`
   with wrapper/manifest paths updated?
2. Should old `docs` phase reports be archived under `docs\research_history`,
   or left in place?
3. Should generated caches (`__pycache__`, `.pytest_cache`) be cleaned later?
4. Should deleted/missing JSON files shown by `git status` be restored,
   ignored, or intentionally removed from tracking?

My recommendation:

```text
Do not move sealed/live files.
First clean only reports and documentation indexes.
Then handle old experiments/reviews/archive folders.
```
