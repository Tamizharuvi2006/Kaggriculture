# L+ ML Dataset Audit

Scope: offline extraction from cached raw replays only. No games or training were run.

Status: **PASS_WITH_LIMITATIONS**
Valid complete replays: **20**
Rows: **28760**
Train rows / validation rows: **23008 / 5752**

## Dataset

Each row is one pre-decision state for one seat and one replay step. Features contain current own/public state and prior-step replay-observable action summaries. Future-derived prices and outcomes are labels only.

## Labels

Adverse next-clearance movement: relative price change <= -15%.
Favorable next-clearance opportunity: relative price change >= 10%.
The weak existing-mode label records the observed first sell priority. It is not a causal ranking label.

## Class Balance

MILK adverse/favorable positives: 4424 / 4268.
STRAWBERRY adverse/favorable positives: 2328 / 1084.
WOOL adverse/favorable positives: 2734 / 1456.

## Leakage And Legal Observability

- PASS: future label fields are excluded from features.
- PASS: current opponent actions are excluded; only prior replay-observable summaries are included.
- PASS: opponent private inventory is excluded.
- PASS: terminal MCV is not a feature or primary target.
- PASS: train/validation split is by complete match, with a chronological held-out tail.
- LIMITATION: raw replays do not contain native accepted/rejected/preempted flags.
- LIMITATION: the available reduced-dataset join has 0 matching rows for these 20 raw replays; downstream wealth labels remain null.

## Decision

The dataset passes structural leakage and observability checks for offline prediction, with the limitations above. It does not yet justify model training or a causal policy claim. Downstream-wealth joins and label-quality review should be completed before training.
