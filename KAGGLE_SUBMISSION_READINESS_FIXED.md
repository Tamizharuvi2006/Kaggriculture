# APEX 4.0 Fixed Submission Readiness

Audit date: 2026-08-22  
Scope: new candidate artifact only. No upload and no Gate 1 execution.

## Candidate

- New filename: `APEX4_SUBMISSION_CANDIDATE_FIXED.py`
- SHA-256: `4b4527021aeffb98275b0202553961aa19ceb9f0db08b8960da3f328888e4750`
- Source preserved unchanged: `APEX4_SUBMISSION_FINAL.py`
- Source SHA-256: `0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a`
- New size: 312,777 bytes
- New line count: 4,518

## Effective Entry Point

The new candidate has exactly one top-level `agent(obs, configuration=None)` definition. Its body is:

```python
return _base_agent(obs)
```

`_base_agent` is the existing intended APEX 4.0 implementation. It selects the configured v18 closed-loop schedule and applies the existing APEX 4.0 board adaptation. The later APEX 3.5 monolithic override was removed from the new candidate only.

## Validation

| Check | Result |
|---|---|
| Old sealed candidate unchanged | PASS |
| New candidate syntax parse | PASS |
| Exactly one top-level `agent` | PASS |
| Effective agent delegates to `_base_agent` | PASS |
| APEX 3.5 override marker present | PASS: absent |
| Imports | PASS: `base64`, `json`, `math`, `zlib`, `__future__` only |
| Direct `kaggle_environments` dependency | PASS: absent |
| NumPy/PyTorch/Pandas dependency | PASS: absent |
| Local file reads | PASS: none detected |
| Network/subprocess dependencies | PASS: none detected |
| Hand-built observation smoke test | PASS: valid action keys returned |
| Gate 1 certification | **NOT CLAIMED** |
| Kaggle upload | **NOT PERFORMED** |

## Exact Diff

See `APEX4_SUBMISSION_CANDIDATE_FIXED.diff`.

The mechanical change is limited to removing the sealed file's final APEX 3.5 block from line 4515 through EOF and adding the four-line APEX 4.0 export wrapper. No APEX 4.0 policy function or strategy parameter was changed.

## Risks And Boundaries

- This is a newly generated, uncertified candidate and has no Gate 1 result.
- The local simulator package remains unavailable; the smoke test was static/module-level only, not a game run.
- The candidate must still be evaluated under a separately sealed canonical environment before any upload.
- The original sealed candidate remains historical evidence and was not overwritten.

## Rollback

- Live rollback: `submission.py`
- Archived rollback: `APEX35_ROLLBACK_ARCHIVE/submission_apex35_prod_backup.py`
- Rollback SHA-256: `78738c1b8bad8fbd2f18a29a1caced8dae0a6adacbc02d6e59decc0fdb130cbb`
