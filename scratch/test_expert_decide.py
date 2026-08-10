"""Test LPlusExpert.decide step-by-step to capture exact return value and exception.
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.expert import LPlusExpert

def test_expert():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})
    obs = env.reset()[0]["observation"]

    expert = LPlusExpert()
    
    # Test step 0, 1, 10, 50, 100
    for s in [0, 1, 10, 50, 100]:
        obs_copy = dict(obs)
        obs_copy["step"] = s
        obs_copy["day"] = s // 24
        obs_copy["hour"] = s % 24
        
        act = expert.decide(obs_copy)
        print(f"Step {s}: Hands count = {len(act.get('hands', []))}, Market = {act.get('market', [])}", flush=True)

if __name__ == "__main__":
    test_expert()
