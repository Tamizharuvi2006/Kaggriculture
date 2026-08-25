"""
Inspect tile lifecycle representation across 250 steps
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import agent as base_agent


def trace_tile_lifecycle():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    
    for step in range(220):
        state = env.step(["PASS", "PASS"])[0]
        obs = state["observation"]
        farms = obs.get("farms", [])
        if farms:
            p0 = farms[0]
            tiles = p0.get("tiles", [])
            # Inspect NW tile (1, 1) and SW tile (7, 3)
            t11 = tiles[1][1] if len(tiles) > 1 and len(tiles[1]) > 1 else None
            t73 = tiles[7][3] if len(tiles) > 7 and len(tiles[7]) > 3 else None
            if step in (0, 75, 152, 156, 163, 170, 180, 200, 211, 215):
                print(f"Step {step:03d} | NW (1, 1): {t11} | SW (7, 3): {t73}")


if __name__ == "__main__":
    trace_tile_lifecycle()
