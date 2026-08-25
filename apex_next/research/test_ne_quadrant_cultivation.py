"""
Test NE Quadrant (Rows 0..4, Cols 5..9) Cultivation via EAST worker movement
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _copy_action, _get, agent as base_agent


def ne_cultivation_agent(obs):
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    
    # Run baseline agent first
    act = base_agent(obs)
    copied = _copy_action(act)
    
    if len(farms) > player:
        own_farm = farms[player]
        unlocked = own_farm.get("unlocked_quadrants", [])
        tiles = own_farm.get("tiles", [])
        hands = copied.get("hands", [])
        
        # When 'NE' is unlocked (Step 170+), deploy Worker #4 to NE tile (2, 6)
        if 'NE' in unlocked and step >= 172 and len(hands) >= 5:
            # Worker #4 moves EAST into NE quadrant
            if step in (172, 173, 174):
                copied["hands"][4] = ["EAST"]
            elif step == 175:
                copied["hands"][4] = ["TILL"]
            elif step == 176:
                copied["hands"][4] = ["PLANT", "STRAWBERRY"]
            elif step == 177:
                copied["hands"][4] = ["WATER"]
            elif step in (178, 179):
                copied["hands"][4] = ["WEST"]  # Return to shed
            elif step == 180:
                copied["hands"][4] = ["PASS"]
                
    return copied


def run_test():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    cand_env = env.run([ne_cultivation_agent, base_agent])
    
    for s in [170, 174, 175, 176, 177, 178, 200, 224, 225]:
        if s < len(cand_env):
            state = cand_env[s][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                tiles = p0.get("tiles", [])
                t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
                print(f"Step {s:03d} | NE Tile (2, 6): {t26}")


if __name__ == "__main__":
    run_test()
