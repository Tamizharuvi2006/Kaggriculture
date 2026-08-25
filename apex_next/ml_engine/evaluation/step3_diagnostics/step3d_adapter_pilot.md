# Step 3C Opponent Observation Probe

Status: `PASS`
Sample steps: `[0, 100, 200, 400, 600, 718]`

## Opponent Execution Summary

### apex35_live_submission

- Opponent calls: `719`
- Non-PASS farmer actions: `674`
- Non-empty market actions: `492`
- Agent0 view of farms[1] final: `{'money': 107331.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 4}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 110361.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### apex4_self_play

- Opponent calls: `719`
- Non-PASS farmer actions: `674`
- Non-empty market actions: `492`
- Agent0 view of farms[1] final: `{'money': 112064.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 112183.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### v18_baseline

- Opponent calls: `719`
- Non-PASS farmer actions: `674`
- Non-empty market actions: `491`
- Agent0 view of farms[1] final: `{'money': 99281.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 99609.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### pass_only

- Opponent calls: `719`
- Non-PASS farmer actions: `0`
- Non-empty market actions: `0`
- Agent0 view of farms[1] final: `{'money': 3000.0, 'quadrant_count': 1, 'workers': 0, 'animals': {'COW': 0, 'SHEEP': 0}, 'planted_tiles': 0, 'crop_counts': {'WHEAT': 0, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 0, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 135572.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

## Conclusion

The seat-1 adapter is working for the imported APEX-style opponents. APEX35, APEX4 self-play, and v18 now produce non-PASS farmer actions and develop the actual farms[1] state observed by agent0. The pass-only control remains undeveloped as expected.

Adapter pilot passed: `True`
Developed imported opponents: `3/3`
Developed agent1-view farms[0]: `4`
Developed agent0-view farms[1]: `3`

Run a small replacement collection with opponent action telemetry and confirm Step 3 labels have class diversity before any 100-game or 1,000-game run.
