# Historical Kaggriculture Environment Reconstruction

Date: 2026-08-22
Scope: read-only reconstruction. No game or smoke run was executed.

## Recovered environment

- Interpreter: `C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Python: `3.12.13`
- Package: `kaggle-environments 1.32.6`
- Package path: `C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\kaggle_environments\__init__.py`
- Distribution metadata: `C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\kaggle_environments-1.32.6.dist-info`
- Kaggriculture module: `C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\kaggle_environments\envs\kaggriculture\kaggriculture.py`
- Registration data: `...\envs\kaggriculture\kaggriculture.json`

Read-only import verification with this interpreter reported:

- `kaggle_environments.__version__ == 1.32.6`
- `kaggle_environments.__file__` equals the package path above
- `kaggriculture` is present in `kaggle_environments.environments`
- `kaggriculture_beginner` is also registered

## Registration mechanism

The package `__init__.py` enumerates `kaggle_environments\envs`, imports each environment module, and calls `register(...)` with that module's interpreter, renderer, and specification. The `kaggriculture` directory contains the backend Python module and JSON specification required by that registration.

## Link to the successful acceptance artifact

`apex_next/ml_engine/evaluation/step1_environment/step1_acceptance_report.json` records:

- `kaggle_environments.make('kaggriculture')`
- 10 completed episodes
- 719 transitions per episode, 7,190 total
- no exceptions

The bundled runtime package was created on 2026-08-14; the acceptance script and report were created on 2026-08-18. It is the only discovered local Python runtime containing the exact `1.32.6` package and the Kaggriculture backend/registration. The project runner imports `kaggle_environments` directly and does not provide a repository-local implementation.

## Launch command reconstruction

The command compatible with the acceptance script and recovered environment is:

```powershell
& 'C:\Users\aruvi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' apex_next\ml_engine\evaluation\step1_acceptance.py
```

The acceptance JSON does not preserve the historical executable path or shell command, so this command is a reconstruction from the script defaults and the only matching installed runtime, not a directly logged command. The environment/package/module identity is recovered exactly; the historical command-line provenance is not independently recorded.

## Gate status

The known-good environment has been located and its registration has been verified without running a game. The next permitted action is a separate smoke test using this exact interpreter, requiring 720 calls / 719 transitions before any MILK-only paired test. No smoke test or MILK test was run in this audit.

