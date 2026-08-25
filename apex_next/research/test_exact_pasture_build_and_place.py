"""
Test building 2 NE pasture tiles at (1, 6) & (2, 6) and placing 2 cows
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _copy_action, _get, agent as base_agent


def ne_cow_agent(obs):
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    
    act = base_agent(obs)
    copied = _copy_action(act)
    
    if len(farms) > player:
        own_farm = farms[player]
        unlocked = own_farm.get("unlocked_quadrants", [])
        hands = copied.get("hands", [])
        
        # Step 152: Buy Land
        if step == 152:
            copied["market"].append(["BUY_LAND"])
            
        # Step 250: Worker #4 builds Pasture at (1, 6) and Worker #5 at (2, 6)
        if 'NE' in unlocked and len(hands) >= 6:
            # Move Worker #4 to (1, 6)
            if step in (240, 241, 242):
                copied["hands"][4] = ["EAST"]
                copied["hands"][5] = ["EAST"]
            elif step == 243:
                copied["hands"][4] = ["NORTH"]
                copied["hands"][5] = ["PASS"]
            elif step == 244:
                copied["hands"][4] = ["BUILD_PASTURE"]
                copied["hands"][5] = ["BUILD_PASTURE"]

        # Step 260: Buy 2 Cows + 8 Wheat
        if step == 260:
            copied["market"].append(["BUY_ANIMAL", "COW", 2])
            copied["market"].append(["BUY_PRODUCT", "WHEAT", 8])

        # Step 261-268: Worker #4 & #5 pickup cows and place
        if 'NE' in unlocked and len(hands) >= 6:
            if step in (261, 262, 263):
                copied["hands"][4] = ["WEST"]
                copied["hands"][5] = ["WEST"]
            elif step == 264:
                copied["hands"][4] = ["PICKUP", "COW"]
                copied["hands"][5] = ["PICKUP", "COW"]
            elif step in (265, 266, 267):
                copied["hands"][4] = ["EAST"]
                copied["hands"][5] = ["EAST"]
            elif step == 268:
                copied["hands"][4] = ["PLACE", "COW"]
                copied["hands"][5] = ["PLACE", "COW"]

    return copied


def run_test():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    cand_env = env.run([ne_cow_agent, base_agent])
    
    for s in [240, 244, 245, 260, 264, 268, 269, 300]:
        if s < len(cand_env):
            state = cand_env[s][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                tiles = p0.get("tiles", [])
                t16 = tiles[1][6] if len(tiles) > 1 and len(tiles[1]) > 6 else None
                t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
                print(f"Step {s:03d} | NE (1, 6): {t16} | NE (2, 6): {t26}")


if __name__ == "__main__":
    run_test()
