# Kaggriculture Environment Registration Diagnostic

Date: 2026-08-22
Scope: read-only environment diagnosis only.

## Verdict

The MILK-only experiment did not produce a valid game result. The failure is an environment restoration problem, not a failed MILK hypothesis.

The repository's documented/current interpreter location is:

`C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe`

Its `site-packages` directory exists, but a read-only package scan found no `kaggle_environments` package, no `kaggriculture` module, and no matching distribution metadata. Therefore the claim that the current environment is a working `kaggle_environments 1.32.6` installation is not supported by the files currently present at that interpreter location.

The old Python 3.11 site-packages path hard-coded in several historical scripts,
`C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages`, does not exist on this machine. The current user's corresponding Python 3.11 user site also does not exist. No Python launcher or `python` command is available on PATH; only the documented Python 3.13 path is present.

## Known-good reference

`apex_next/ml_engine/evaluation/step1_environment/step1_acceptance_report.json` is the strongest local evidence of the previously successful setup:

- `kaggle_environments.make('kaggriculture')`
- 10 episodes completed
- 719 transitions per episode, 7,190 total
- no exceptions
- Python 3.13 and Kaggle environment v1.32.6 are documented by the project
- feature and action-format checks passed

The research runner also imports `kaggle_environments` directly in `apex_next/research/match_runner.py`; it does not contain a repository-local fallback registration. The root requirements file only declares `kaggle-environments>=1.14.0`, so the package and its Kaggriculture registration must come from the Python environment rather than from this repository.

## Root cause

The current Python 3.13 environment is incomplete or pointed at a different site-packages set than the one used for the successful acceptance run. The missing package/module explains why the runner can fail before a real Kaggriculture episode begins and why a two-call result must not be interpreted as an experiment outcome.

This audit did not run a game, invoke the MILK experiment, reinstall packages, or alter any source, checkpoint, submission, or production file.

## Minimal restoration procedure

These are restoration steps, not actions performed in this audit:

1. Locate the original interpreter or environment that generated the acceptance report and contains both `kaggle_environments` version `1.32.6` and the `kaggriculture` registration.
2. Confirm package provenance with that interpreter: its executable path, `kaggle_environments.__file__`, distribution version, and the registration mechanism/module path for `kaggriculture`.
3. Use that exact interpreter for the research runner. Do not rely on PATH resolution, the stale `43731140` path, or a fresh unpinned installation.
4. Before any MILK test, run only the existing environment smoke gate and require a real Kaggriculture episode with exactly 720 calls / 719 transitions, no exception, and the expected action/observation checks.
5. If the known-good package cannot be located, stop this research line rather than reinstalling or changing the frozen candidate speculatively.

## Current experiment status

- MILK-ranker hypothesis: unvalidated by a paired 720-step run.
- Factorial and cached-trace evidence: unchanged and still usable within its stated limits.
- PPO, V4.1, L+, v18, Land #4 logic, reward logic, checkpoints, and production files: untouched.
- New game run: not justified until the environment smoke gate passes.

