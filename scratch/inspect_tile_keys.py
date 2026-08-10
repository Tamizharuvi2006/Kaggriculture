"""Print raw tile dictionary keys and sample tile object.
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def inspect_tiles():
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    spec_a = importlib.util.spec_from_file_location("apex_mod", apex_path)
    apex_mod = importlib.util.module_from_spec(spec_a)
    spec_a.loader.exec_module(apex_mod)

    spec_o = importlib.util.spec_from_file_location("opp_mod", opp_path)
    opp_mod = importlib.util.module_from_spec(spec_o)
    spec_o.loader.exec_module(opp_mod)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})

    tile_samples = []

    def debug_wrapper(obs, config=None):
        farms = obs.get("farms", [])
        if farms:
            my_farm = farms[0]
            raw_tiles = my_farm.get("tiles", [])
            if raw_tiles and len(tile_samples) < 5:
                # Flatten tiles if list of lists
                flat_tiles = [t for row in raw_tiles for t in (row if isinstance(row, list) else [row])]
                tile_samples.append((obs.get("day"), obs.get("hour"), flat_tiles[0] if flat_tiles else None))
        return apex_mod._POLICY.select_action(obs, apex_mod.WorldState(obs))

    env.run([debug_wrapper, opp_mod.agent])

    print(f"Captured {len(tile_samples)} raw tile samples:", flush=True)
    for day, hour, t in tile_samples:
        print(f"  Day {day} Hour {hour} Tile Keys: {list(t.keys()) if isinstance(t, dict) else type(t)}", flush=True)
        print(f"  Day {day} Hour {hour} Tile Content: {t}", flush=True)

if __name__ == "__main__":
    inspect_tiles()
