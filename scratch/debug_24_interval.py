"""Debug 24-step townCenterSellInterval in kaggle_environments.
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def load_v41_baseline():
    v41_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("v41_mod", v41_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

v41 = load_v41_baseline()

print("1. Testing default configuration (no custom config overrides):")
env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env1.run([v41, v41])
print("   Default env steps count:", len(env1.steps))
print("   Default env final money player 0:", env1.steps[-1][0]["observation"]["farms"][0].get("money"))
print("   Default env final money player 1:", env1.steps[-1][1]["observation"]["farms"][1].get("money"))

print("\n2. Testing townCenterSellInterval: 24 custom configuration:")
try:
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": 42})
    env2.run([v41, v41])
    print("   Custom env steps count:", len(env2.steps))
    print("   Custom env final money player 0:", env2.steps[-1][0]["observation"]["farms"][0].get("money"))
    print("   Custom env final money player 1:", env2.steps[-1][1]["observation"]["farms"][1].get("money"))
    if len(env2.steps) > 5 and "status" in env2.steps[1][0]:
        print("   Step 1 status:", env2.steps[1][0].get("status"))
        print("   Step 1 info:", env2.steps[1][0].get("info"))
except Exception as err:
    print("   Error running custom config:", err)
