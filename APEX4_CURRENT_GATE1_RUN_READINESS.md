# Current APEX 4.0 Gate 1 Run Readiness

The current candidate is now sealed for a future canonical Gate 1 measurement:

- Candidate: `APEX4_SUBMISSION_FINAL.py`
- SHA-256: `0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a`
- Baseline: `submission.py`
- Baseline SHA-256: `78738c1b8bad8fbd2f18a29a1caced8dae0a6adacbc02d6e59decc0fdb130cbb`
- Seeds: 46, expanded to 92 seat-balanced matches
- Required engine: `kaggle-environments 1.32.6`, registered `kaggriculture`
- Horizon: 720 steps

The historical 50.0% result files are explicitly excluded because they do not contain the current candidate hash and their adjacent verdicts reference older candidate hashes.

## Execution Status

**NOT EXECUTED.** The currently available interpreter cannot import `kaggle_environments`. Installing or repairing the package would create an unsealed environment and is not authorized by this manifest.

Before execution, bind the exact interpreter, package/module identity, registration files, evaluator process, and full configuration. Then run one new Gate 1 and write a new dated result containing this manifest hash. Do not overwrite historical results.
