# APEX 4.0 Gate 1 Environment Binding Audit

Date: 2026-08-22  
Scope: read-only historical environment recovery. No package installation and no Gate 1 rerun.

## Verdict

**PROVENANCE INCOMPLETE: reference environment recovered, Gate 1 binding not proven.**

The repository contains strong evidence for a prior working Kaggriculture environment, but the preserved APEX 4.0 Gate 1 result does not record enough environment identity to prove that it ran in that exact interpreter/package instance.

## Recovered Reference Environment

The existing reconstruction record identifies:

- Interpreter: `C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Python: 3.12.13
- Package: `kaggle-environments 1.32.6`
- Package module: `kaggle_environments\__init__.py`
- Kaggriculture backend: `envs\kaggriculture\kaggriculture.py`
- Registration specification: `envs\kaggriculture\kaggriculture.json`
- Historical registration names: `kaggriculture`, `kaggriculture_beginner`

These details are recorded in `historical_environment_reconstruction.md/json` and were linked to the Step 1 acceptance artifact.

## What The Acceptance Artifact Proves

`apex_next/ml_engine/evaluation/step1_environment/step1_acceptance_report.json` records:

- `kaggle_environments.make('kaggriculture')`
- 10 completed episodes
- 719 transitions per episode
- 7,190 total transitions
- no exceptions

This proves that a working Kaggriculture environment existed for that acceptance run. It does **not** prove that the APEX 4.0 Gate 1 run used the same interpreter, package files, evaluator commit, or configuration.

## Gate 1 Binding Evidence

The preserved Gate 1 results are:

- `apex_next/apex4/results/gate1.json`
- `apex_next/research/EXP-0155/results/gate1.json`

They contain 46 seed records and 50.0% over 92 seat-balanced matches. They do not contain:

- interpreter executable path
- Python version
- `kaggle_environments.__file__`
- package distribution version or package hash
- Kaggriculture backend/specification hash
- evaluator source commit or source hash
- complete configuration object/hash
- candidate SHA-256 inside the result file
- explicit command line

The evaluator source documents the intended contract in `apex_next/research/gate_runner.py` and `apex_next/research/match_runner.py`, including `episodeSteps=720`, the two seat orders, and the recorded historical engine label `kaggle_environments v1.32.6`. Source documentation is not execution-time provenance.

## Current Machine Check

The current Python 3.12.13 interpreter path identified above no longer imports `kaggle_environments`; package import failed with `ModuleNotFoundError`. No installation or repair was attempted. This means the recovered environment is a historical description/reference, not a currently runnable verified environment.

## Required Evidence To Complete Binding

Recover at least one contemporaneous artifact tied to the Gate 1 run containing:

1. interpreter path and Python version
2. package path/version and file or distribution hash
3. Kaggriculture backend/specification identity
4. evaluator source commit or content hash
5. full configuration and `episodeSteps`
6. candidate and baseline hashes
7. exact 46-seed manifest or seed hash
8. command or process record linking these identities to `gate1.json`

Until these are recovered, the 50.0% result remains valid immutable historical evidence, but a canonical revalidation is not yet authorized.
