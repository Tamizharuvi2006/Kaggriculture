# Step 3B Label Diagnostics

Source dataset: `apex_next\ml_engine\data\expert_demos_step3f_targeted_pilot_25.npz`
Transitions: `17975`
Episodes: `25`

## Rule Hit Counts

- LIVESTOCK_HEAVY episodes: `5`
- CROP_HEAVY episodes: `0`
- AGGRESSIVE_EXPAND episodes: `5`
- MARKET_MANIPULATOR episodes: `not derivable`

## Key Observed Maxima

- Max opponent cows + sheep, any transition: `14.0`
- Max final opponent cows + sheep: `13.0`
- Max opponent strawberry tiles, any transition: `40.0`
- Max final opponent strawberry tiles: `6.0`
- Max opponent land count, any transition: `3.0`
- Step 200 opponent-ahead count: `5`
- Max opponent worker count: `12.0`

## Market Telemetry

- Expert raw actions available: `True`
- Expert executed actions available: `True`
- Opponent actions available: `True`
- Opponent sell patterns available: `True`

## Conclusion

The current Step 2 dataset is valid but does not contain genuine multi-class opponent archetype evidence.

Step 4 remains blocked.
