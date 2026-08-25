"""
Test Pasture 3 Construction at (2, 7) and Cow Placement in kaggle_environments v1.32.6
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _copy_action, _get, agent as base_agent


def pasture3_test_agent(obs):
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    
    act = base_agent(obs)
    copied = _copy_action(act)
    
    if len(farms) > player:
        own_farm = farms[player]
        unlocked = own_farm.get("unlocked_quadrants", [])
        pastures = own_farm.get("pastures", [])
        hands = copied.get("hands", [])
        
        # Step 152: Buy Land
        if step == 152:
            copied["market"].append(["BUY_LAND"])
            
        # Step 283-287: Workers #4 and #5 move EAST from shed (3, 3) to NE site (2, 7)
        if 'NE' in unlocked and len(hands) >= 6:
            if step in (283, 284, 285, 286):
                copied["hands"][4] = ["EAST"]
                copied["hands"][5] = ["EAST"]
            elif step == 287:
                copied["hands"][4] = ["NORTH"]
                copied["hands"][5] = ["NORTH"]
            elif step == 288:
                # Arrived at (2, 7) and (2, 8)
                copied["hands"][4] = ["BUILD_PASTURE"]
                copied["hands"][5] = ["BUILD_PASTURE"]

        # Step 312: Buy 4 Cows + 16 Wheat
        if step == 312:
            copied["market"].append(["BUY_ANIMAL", "COW", 4])
            copied["market"].append(["BUY_PRODUCT", "WHEAT", 16])

        # Step 313-318: Worker #4 & #5 pickup cows and place in Pasture 3
        if 'NE' in unlocked and len(hands) >= 6:
            if step == 313:
                copied["hands"][4] = ["WEST"]
                copied["hands"][5] = ["WEST"]
            elif step in (314, 315, 316):
                copied["hands"][4] = ["WEST"]
                copied["hands"][5] = ["WEST"]
            elif step == 317:
                copied["hands"][4] = ["PICKUP", "COW", 2]
                copied["hands"][5] = ["PICKUP", "COW", 2]
            elif step in (318, 319, 320, 321):
                copied["hands"][4] = ["EAST"]
                copied["hands"][5] = ["EAST"]
            elif step == 322:
                copied["hands"][4] = ["NORTH"]
                copied["hands"][5] = ["NORTH"]
            elif step == 323:
                copied["hands"][4] = ["PLACE", "COW", 2]
                copied["hands"][5] = ["PLACE", "COW", 2]

    return copied


def run_pasture3_test():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    cand_env = env.run([pasture3_test_agent, base_agent])
    
    for s in [280, 288, 289, 312, 313, 317, 323, 324, 350, 400]:
        if s < len(cand_env):
            state = cand_env[s][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                pastures = p0.get("pastures", [])
                workers = p0.get("workers", [])
                w4_pos = (workers[4]["r"], workers[4]["c"]) if len(workers) > 4 else None
                w5_pos = (workers[5]["r"], workers[5]["c"]) if len(workers) > 5 else None
                total_animals = sum(len(p.get("animals", [])) for p in pastures)
                print(f"Step {s:03d} | Pastures: {len(pastures)} | Total Animals: {total_animals} | W4 Pos: {w4_pos} | W5 Pos: {w5_pos}")


if __name__ == "__main__":
    run_pasture3_test()
