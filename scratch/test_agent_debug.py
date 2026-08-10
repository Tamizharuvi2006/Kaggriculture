"""Inspect expert action output type and content.
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.expert import LPlusExpert

def inspect_expert_act():
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    spec_o = importlib.util.spec_from_file_location("opp_mod", opp_path)
    opp_mod = importlib.util.module_from_spec(spec_o)
    spec_o.loader.exec_module(opp_mod)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})

    obs = env.reset()[0]["observation"]
    expert = LPlusExpert()
    expert_act = expert.decide(obs)

    print(f"Expert Action Output Type: {type(expert_act)}", flush=True)
    print(f"Expert Action Output Content: {expert_act}", flush=True)

if __name__ == "__main__":
    inspect_expert_act()
