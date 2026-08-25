# APEX 4.0 Gate 1 Provenance Reconciliation

Date: 2026-08-22  
Scope: read-only reconciliation. Gate 1 was not rerun.

## Conclusion

**67.4% was a stale/incorrect projection, not the executed Gate 1 result.**

The figure appears in macro/projection artifacts as `31 / 46 projected loss recovery (67.4%)`. The preserved executable Gate 1 results for the exact 46-seed set both calculate to 50.0% over 92 seat-balanced matches. No executed result containing 31 wins out of the 46 seeds was found.

## Reconciled Chain

### Candidate

- File: `APEX4_SUBMISSION_FINAL.py`
- SHA-256: `0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a`
- The release manifest, entrypoint diagnostic, and observed file agree on this hash.

### Baseline

- File: `submission.py`
- SHA-256: `78738c1b8bad8fbd2f18a29a1caced8dae0a6adacbc02d6e59decc0fdb130cbb`
- The rollback archive has the same hash.

### Exact seed set

- Source: `reports/live_match_telemetry/apex33_loss_seeds_cache.json`
- Count: 46 unique seeds
- Sorted-seed manifest hash: `26b4c048112826f5aad19fc95394d5887d8a53137f17550e7d96cc801f8e12ea`
- Gate construction: two seat orders per seed, producing 92 matches.

### Evaluator contract

The preserved evaluator is described by:

- `apex_next/research/gate_runner.py`
- `apex_next/research/match_runner.py`

Its recorded contract is:

- baseline loaded from `submission.py`
- candidate passed explicitly by experiment path
- `kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})`
- both seat orders run for each seed
- candidate win points: win = 1, tie = 0.5, loss = 0
- Gate 1 pass threshold: win rate >= 0.60

Historical project records identify the simulator as `kaggle_environments v1.32.6`. The current local Python environment does not contain that package, so package availability and exact engine bytes were not independently re-executed in this audit. No installation was attempted.

## Executed Gate 1 Evidence

Both files contain 46 records with the same seed-level results:

- `apex_next/apex4/results/gate1.json`
- `apex_next/research/EXP-0155/results/gate1.json`

Offline calculation from either file:

```text
seed records       46
seat-balanced games 92
win points          46.0
calculated WR       46.0 / 92 = 0.5000
errors              0
threshold           0.6000
verdict             FAIL
```

The result records do not embed candidate hash, evaluator commit, engine package hash, or full configuration manifest. Those fields must be added or recovered before a canonical revalidation.

## Source Of 67.4%

The 67.4% value is explicitly attached to projected/modelled recovery in:

- `apex_next/apex4/research/audit_macro_economic_models.py`
- `reports/APEX4_MACRO_ECONOMIC_REPORT.md`
- `reports/APEX4_MACRO_MODELS_ANALYSIS.json`
- `reports/APEX4_NE_4TILE_FEASIBILITY.md/json`

The model table includes multiple projections, including 42/46, 31/46, 38/46, 18/46, and 22/46. The `31/46` projection was later copied into:

- `APEX4_RELEASE_MANIFEST.json`
- `APEX4_PROVENANCE.json`
- `reports/PROJECT_STATE.md`

Those files incorrectly label the projection as an official executed Gate 1 result.

## Final Gate

The provenance chain is sufficient to establish the failure and explain the contradiction, but not sufficient to authorize revalidation yet. Before rerunning Gate 1, recover or pin:

1. exact historical Python/interpreter environment
2. `kaggle_environments` package and engine provenance
3. evaluator commit/source hash
4. full configuration and candidate path/hash embedded in the result manifest
5. immutable 46-seed manifest attachment

The 50.0% result must remain unchanged as historical evidence. A future revalidation must produce a separate dated artifact.
