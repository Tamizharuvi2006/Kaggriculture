# APEX 4.0 Gate 1 Provenance Audit

Date: 2026-08-22  
Scope: read-only historical record reconciliation. No games, uploads, or artifact changes were performed.

## Authoritative Finding

The authoritative executable Gate 1 result currently present in the repository is:

**FAIL: 46.0 win points across 46 seed pairs, equivalent to 46/92 = 50.0% seat-balanced match win rate.**

This result is present in both:

- `apex_next/apex4/results/gate1.json`
- `apex_next/research/EXP-0155/results/gate1.json`

The two files contain the same 46 seed records and the same 50.0% summary. The gate runner's documented rule is `WR >= 0.60`; therefore this result falsifies Gate 1 and should stop the release pipeline.

## Seed And Artifact Evidence

| Item | Evidence |
|---|---|
| Gate 1 seed source | `reports/live_match_telemetry/apex33_loss_seeds_cache.json` |
| Seed count | 46 unique cached seeds |
| Match accounting | 2 seats per seed = 92 paired matches |
| Candidate file | `APEX4_SUBMISSION_FINAL.py` |
| Candidate SHA-256 | `0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a` |
| Baseline file | `submission.py` |
| Baseline SHA-256 | `78738c1b8bad8fbd2f18a29a1caced8dae0a6adacbc02d6e59decc0fdb130cbb` |
| Gate result errors | 0 in the preserved result records |

The result JSON does not embed the candidate hash, evaluator commit, engine package hash, or a complete configuration manifest. Those missing fields prevent stronger independent reproduction from the result file alone, but they do not change the observed 50.0% result.

## Origin Of 67.4%

The 67.4% number is present in:

- `APEX4_RELEASE_MANIFEST.json`
- `APEX4_PROVENANCE.json`
- `reports/PROJECT_STATE.md`
- `reports/APEX4_MACRO_ECONOMIC_REPORT.md/json`
- `reports/APEX4_NE_4TILE_FEASIBILITY.md/json`

The macro/projection records describe **“31 / 46 projected loss recovery (67.4%)”**. They are not the preserved executed Gate 1 result. No result file containing 31 wins out of these 46 Gate 1 seeds was found. The release manifest therefore appears to have converted a projected or intermediate estimate into a certified Gate 1 measurement.

## Contradiction Resolution

The following records are invalid as a certification bundle until corrected:

- `APEX4_RELEASE_MANIFEST.json`: claims Gate 1 passed at 67.4% and release ready.
- `APEX4_PROVENANCE.json`: repeats the 67.4% claim as an official replay result.
- `reports/PROJECT_STATE.md`: repeats the 67.4% claim and all-gates-passed status.

The following records agree with the executable result and should be treated as the current authoritative release decision:

- `reports/APEX4_GATE_REPORT.json`: Gate 1 50.0%, `FALSIFIED_GATE_1`.
- `reports/APEX4_RELEASE_DECISION.md`: Gate 1 failed, production rejected.
- `apex_next/apex4/results/gate1.json`: 46 records, 50.0%.
- `apex_next/research/EXP-0155/results/gate1.json`: 46 records, 50.0%.

## Decision

**APEX 4.0 is not certified for live validation.** APEX 3.5 remains the live baseline. The manifest/provenance/state-summary files should be re-issued or explicitly invalidated after preserving this audit. No live match should be spent until that governance correction is made.
