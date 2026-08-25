# Step 3C Opponent Observation Probe

Status: `PASS`
Sample steps: `[0, 100, 200, 400, 600, 718]`

## Opponent Execution Summary

### apex35_live_submission

- Opponent calls: `719`
- Non-PASS farmer actions: `0`
- Non-empty market actions: `719`
- Agent0 view of farms[1] final: `{'money': 0.0, 'quadrant_count': 1, 'workers': 0, 'animals': {'COW': 0, 'SHEEP': 0}, 'planted_tiles': 0, 'crop_counts': {'WHEAT': 0, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 0, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 155521.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### apex4_self_play

- Opponent calls: `719`
- Non-PASS farmer actions: `0`
- Non-empty market actions: `719`
- Agent0 view of farms[1] final: `{'money': 0.0, 'quadrant_count': 1, 'workers': 0, 'animals': {'COW': 0, 'SHEEP': 0}, 'planted_tiles': 0, 'crop_counts': {'WHEAT': 0, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 0, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 150852.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### v18_baseline

- Opponent calls: `719`
- Non-PASS farmer actions: `0`
- Non-empty market actions: `719`
- Agent0 view of farms[1] final: `{'money': 0.0, 'quadrant_count': 1, 'workers': 0, 'animals': {'COW': 0, 'SHEEP': 0}, 'planted_tiles': 0, 'crop_counts': {'WHEAT': 0, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 0, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 168172.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

### pass_only

- Opponent calls: `719`
- Non-PASS farmer actions: `0`
- Non-empty market actions: `0`
- Agent0 view of farms[1] final: `{'money': 3000.0, 'quadrant_count': 1, 'workers': 0, 'animals': {'COW': 0, 'SHEEP': 0}, 'planted_tiles': 0, 'crop_counts': {'WHEAT': 0, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 0, 'MELON': 0}}`
- Agent1 view of farms[0] final: `{'money': 89267.0, 'quadrant_count': 3, 'workers': 12, 'animals': {'COW': 8, 'SHEEP': 5}, 'planted_tiles': 7, 'crop_counts': {'WHEAT': 1, 'CARROT': 0, 'TOMATO': 0, 'STRAWBERRY': 6, 'MELON': 0}}`

## Conclusion

Opponent functions were invoked, but APEX-style opponent agents appear to receive the unadapted seat-1 observation and act as if farms[0] is their own farm. Agent0's view of farms[1] stays undeveloped, while agent1's observation farms[0] mirrors agent0's developed farm. Step 2 therefore collected games against opponents that did not develop their actual seat-1 farm.

Developed agent1-view farms[0]: `4`
Developed agent0-view farms[1]: `0`

Add a seat-1 observation adapter for imported APEX-style opponent policies, then run a tiny pilot before any new large collection.
