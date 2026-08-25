# Step 3B Label Diagnostics

Source dataset: `apex_next\ml_engine\data\invalidated\original_seat_bug\expert_demos.npz`
Transitions: `719000`
Episodes: `1000`

## Rule Hit Counts

- LIVESTOCK_HEAVY episodes: `0`
- CROP_HEAVY episodes: `0`
- AGGRESSIVE_EXPAND episodes: `0`
- MARKET_MANIPULATOR episodes: `not derivable`

## Key Observed Maxima

- Max opponent cows + sheep, any transition: `0.0`
- Max final opponent cows + sheep: `0.0`
- Max opponent strawberry tiles, any transition: `0.0`
- Max final opponent strawberry tiles: `0.0`
- Max opponent land count, any transition: `1.0`
- Step 200 opponent-ahead count: `0`
- Max opponent worker count: `8.0`

## Market Telemetry

- Expert raw actions available: `True`
- Expert executed actions available: `True`
- Opponent actions available: `False`
- Opponent sell patterns available: `False`

## Conclusion

The current Step 2 dataset is valid but does not contain genuine multi-class opponent archetype evidence.

Step 4 remains blocked.
