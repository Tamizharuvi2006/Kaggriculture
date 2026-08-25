# APEX 4.0 Gate 1 Binding Finding

Date: 2026-08-22  
Scope: read-only artifact binding audit. No rerun, install, upload, or source change.

## Finding

The preserved 50.0% Gate 1 result is **not cryptographically bound to the current APEX 4.0 release candidate**.

Current release candidate:

- `APEX4_SUBMISSION_FINAL.py`
- SHA-256: `0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a`

Historical Gate 1 verdict metadata names different candidate hashes:

- `apex_next/research/EXP-0155/verdict.json`: `aef5b8d0730af2d1ace6a0beac68ca3b81073a1f32ef9ed9043bb34b1db6c4ef`
- `apex_next/apex4/verdict.json`: `e1123908de7c1a42456dcc998284bc1205db45de2e609867a6bfbed4efe07295`

The actual files match those recorded hashes. Neither equals the current release candidate hash.

## Interpretation

The 50.0% Gate 1 result remains valid historical evidence for an earlier candidate evaluation, but it cannot be used as a certified result for the current `APEX4_SUBMISSION_FINAL.py` without a missing artifact bridge.

This changes the provenance classification:

```text
67.4%: stale/incorrect projection
50.0% current-candidate certification: not proven
50.0% historical result: valid for an earlier candidate, exact identity unresolved between recorded verdicts
```

The result files themselves contain no candidate hash, so the two 50% result copies cannot be independently assigned to `aef5...` versus `e112...` from their contents alone. Their adjacent verdict records show that the repository mixed experiment outputs and release summaries.

## Environment Status

The previously recovered Python 3.12.13 / `kaggle-environments 1.32.6` setup is only a reference environment. The current interpreter no longer imports that package, and the Gate 1 result lacks execution-time environment metadata. Environment binding is therefore also incomplete.

## Decision

Do not treat the 50.0% result as a Gate 1 result for the current release candidate. Do not rerun yet. The next permissible step is to recover an archived run manifest, console transcript, or result-generation record that links one exact candidate hash to one exact Gate 1 result and environment. If no bridge exists, preserve the 50% result as historical evidence and create a newly sealed canonical evaluation record later.
