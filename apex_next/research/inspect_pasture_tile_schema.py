"""
Inspect how pastures and cows are stored in tiles in kaggle_environments v1.32.6
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import agent as base_agent


def trace_pasture_schema():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    cand_env = env.run([base_agent, base_agent])
    
    # In baseline APEX 3.5, Pasture 1 is built at Step 1 and Pasture 2 is built at Step 159.
    for step_idx in [0, 2, 10, 160, 175]:
        if step_idx < len(cand_env):
            state = cand_env[step_idx][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                tiles = p0.get("tiles", [])
                print(f"=== STEP {step_idx:03d} TILES AUDIT ===")
                for r in range(len(tiles)):
                    for c in range(len(tiles[r])):
                        val = tiles[r][c]
                        if val is not None and val != "LOCKED":
                            if isinstance(val, dict):
                                kind = val.get("kind")
                                if kind in ("PASTURE", "BUILD_PASTURE", "FENCE", "ANIMAL") or "pasture" in str(val).lower() or "cow" in str(val).lower():
                                    print(f"  Tile ({r}, {c}): {val}")
                            else:
                                print(f"  Tile ({r}, {c}): {val}")


if __name__ == "__main__":
    trace_pasture_schema()
