# Frozen PPO Transfer-Value Audit

Scope: read-only offline probes against cached replay labels. No games or PPO fine-tuning were run.

Status: **PASS_WITH_LIMITATIONS**
Rows enriched from raw replays: **28760/28760**

The frozen selector has 133 inputs, a 32-unit shared hidden representation, and four outputs: `u_market`, `u_route`, confidence, and value.

Probe AUC is validation-only. `ppo_hidden32` tests the frozen representation, `ppo_outputs4` tests frozen outputs, and `price_trend_baseline` uses current price plus 1/3/6-step trends.

## all_steps

Train rows: 23008; validation rows: 5752.

| Target | PPO hidden | PPO outputs | Price/trend |
|---|---:|---:|---:|
| adverse_milk | 0.698 | 0.503 | 0.701 |
| favorable_milk | 0.845 | 0.496 | 0.809 |
| adverse_strawberry | 0.921 | 0.482 | 0.911 |
| favorable_strawberry | 0.942 | 0.545 | 0.976 |
| adverse_wool | 0.867 | 0.526 | 0.867 |
| favorable_wool | 0.739 | 0.519 | 0.925 |

## decision_step_120

Train rows: 32; validation rows: 8.

| Target | PPO hidden | PPO outputs | Price/trend |
|---|---:|---:|---:|
| adverse_milk | n/a | n/a | n/a |
| favorable_milk | n/a | n/a | n/a |
| adverse_strawberry | n/a | n/a | n/a |
| favorable_strawberry | n/a | n/a | n/a |
| adverse_wool | n/a | n/a | n/a |
| favorable_wool | n/a | n/a | n/a |

## Conclusion

The frozen representation shows mixed predictive transfer and no consistent advantage over simple price/trend features. The step-120 slice has only 32 train and 8 validation rows with single-class validation labels, so it cannot support a transfer claim.

Recommendation: do not reuse the PPO representation as the default market model. Prefer a fresh small supervised market model if later label-quality work justifies training. This audit is predictive only, not causal evidence.
