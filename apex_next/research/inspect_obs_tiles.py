"""
Inspect the exact observation tile schema in kaggle_environments v1.32.6
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def inspect_tiles():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    state = env.step(["PASS", "PASS"])[0]
    obs = state["observation"]
    
    farms = obs.get("farms", [])
    if farms:
        p0 = farms[0]
        print("Keys in farms[0]:", list(p0.keys()))
        tiles = p0.get("tiles", [])
        print(f"Total tiles in farm: {len(tiles)}")
        if tiles:
            print("Sample tile 0:", tiles[0])
            print("Sample tile keys:", list(tiles[0].keys()))
            
        workers = p0.get("workers", [])
        print(f"Total workers: {len(workers)}")
        if workers:
            print("Sample worker 0:", workers[0])
            
    print("Market obs keys:", list(obs.get("market", {}).keys()))


if __name__ == "__main__":
    inspect_tiles()
