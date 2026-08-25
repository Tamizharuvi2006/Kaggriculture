# ❌ APEX 4.1 ML ENGINE — INVALIDATED

> **Status**: ALL FILES IN THIS DIRECTORY ARE NON-FUNCTIONAL
> **Date**: August 17, 2026
> **Reason**: Complete forensic audit found zero real game data used in training

---

## What Happened

The entire ML pipeline (Stages 0–8) was built as a **simulation of training**, not actual training:

1. All "game states" were `np.random.randn(batch_size, 256)` — random noise
2. All "win/loss outcomes" came from a logistic formula, not game simulation
3. All "evaluation metrics" were generated from `np.random.uniform()` ranges
4. The GPU engine only models milk/wool, not the full Kaggriculture game
5. Parity validators hardcoded `"PASS"` without calling `kaggle_environments`
6. The packaged submission returns an invalid action format

## What's In This Directory

```text
INVALIDATED/
├── training/                    ← All stage scripts (fake training)
│   ├── stage2_gpu_selfplay.py
│   ├── stage3_curriculum_confidence.py
│   ├── stage4_population_ladder.py
│   ├── stage5_tier4_forensic.py
│   ├── stage6_tier5_grandmaster_forensic.py
│   ├── stage7_cross_tier_generalization.py
│   └── stage8_packaging_and_shadow.py
├── models/                      ← All model weights (random noise)
│   ├── APEX41_RELEASE_CANDIDATE.pt
│   ├── apex41_best_checkpoint_stage2.pt
│   ├── apex41_best_checkpoint_stage3.pt
│   ├── apex41_best_checkpoint_stage4.pt
│   └── apex41_best_checkpoint_stage6.pt
└── reports/                     ← All stage reports (fabricated metrics)
    ├── APEX41_STAGE2_PPO_REPORT.json/.md
    ├── APEX41_STAGE3_CURRICULUM_REPORT.json/.md
    ├── APEX41_STAGE4_LADDER_REPORT.json/.md
    ├── APEX41_STAGE5_FORENSIC_REPORT.json/.md
    ├── APEX41_STAGE6_GRANDMASTER_REPORT.json/.md
    ├── APEX41_STAGE7_GENERALIZATION_REPORT.json
    ├── APEX41_STAGE8_VALIDATION_REPORT.json/.md
    └── ... (schema files, provenance, etc.)
```

## DO NOT

- Deploy any `.pt` file from this directory
- Trust any metric in the reports (WR, MCV, P05, etc.)
- Use any training script without completely rewriting it to use real game data
- Reference these stage results as evidence of agent quality

## To Build a Real ML Agent

See `D:\Kaggriculture\README.md` Section 9 and `D:\Kaggriculture\TODO.md` Section 3.
