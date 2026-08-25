"""
Test Land 2 (SW Unlock) + Pasture 3 Build at Step 267 + Cow Placement at Step 274
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _copy_action, _get, agent as base_agent


def sw_full_lifecycle_agent(obs):
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    
    act = base_agent(obs)
    copied = _copy_action(act)
    
    if len(farms) > player:
        own_farm = farms[player]
        unlocked = own_farm.get("unlocked_quadrants", [])
        hands = copied.get("hands", [])
        
        # Step 240: Buy Land 2 (Unlocks SW)
        if step == 240:
            copied["market"].append(["BUY_LAND"])
            
        # Step 264-266: Workers #4 and #5 move SOUTH into SW quadrant to build Pasture tiles at (6, 2) & (7, 2)
        if 'SW' in unlocked and len(hands) >= 6:
            if step in (264, 265, 266):
                copied["hands"][4] = ["SOUTH"]
                copied["hands"][5] = ["SOUTH"]
            elif step == 267:
                copied["hands"][4] = ["BUILD_PASTURE"]
                copied["hands"][5] = ["BUILD_PASTURE"]

        # Step 268: Buy 2 Cows + 8 Wheat
        if step == 268:
            copied["market"].append(["BUY_ANIMAL", "COW", 2])
            copied["market"].append(["BUY_PRODUCT", "WHEAT", 8])

        # Step 269-275: Workers #4 & #5 pickup cows and place in SW pasture
        if 'SW' in unlocked and len(hands) >= 6:
            if step in (269, 270, 271):
                copied["hands"][4] = ["NORTH"]
                copied["hands"][5] = ["NORTH"]
            elif step == 272:
                copied["hands"][4] = ["PICKUP", "COW"]
                copied["hands"][5] = ["PICKUP", "COW"]
            elif step in (273, 274, 275):
                copied["hands"][4] = ["SOUTH"]
                copied["hands"][5] = ["SOUTH"]
            elif step == 276:
                copied["hands"][4] = ["PLACE", "COW"]
                copied["hands"][5] = ["PLACE", "COW"]

    return copied


def run_test():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    cand_env = env.run([sw_full_lifecycle_agent, base_agent])
    
    for s in [260, 263, 267, 268, 272, 276, 277, 300, 350, 400]:
        if s < len(cand_env):
            state = cand_env[s][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                unlocked = p0.get("unlocked_quadrants", [])
                tiles = p0.get("tiles", [])
                t62 = tiles[6][2] if len(tiles) > 6 and len(tiles[6]) > 2 else None
                t72 = tiles[7][2] if len(tiles) > 7 and len(tiles[7]) > 2 else None
                print(f"Step {s:03d} | Unlocked: {unlocked} | SW (6, 2): {t62} | SW (7, 2): {t72}")


if __name__ == "__main__":
    run_test()
