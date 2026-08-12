import sys
import os
import kaggle_environments
import importlib.util

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex34 import agent as apex34_agent

def check_apex34_ne_timing():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": 600000})
    trainer = env.train([None, apex34_agent])
    obs = trainer.reset()

    ne_first_step = None
    for s in range(720):
        act = apex34_agent(obs)
        obs, rew, done, info = trainer.step(act)
        farms = obs.get("farms", [])
        if farms:
            tiles = farms[0].get("tiles", [])
            for r_idx in range(5):
                for c_idx in range(5, 10):
                    if r_idx < len(tiles) and c_idx < len(tiles[r_idx]):
                        cell = tiles[r_idx][c_idx]
                        if isinstance(cell, dict) and cell.get("kind") == "PLANT" and cell.get("crop") == "STRAWBERRY":
                            if ne_first_step is None:
                                ne_first_step = s
                                print(f"APEX 3.4 Seed 600000 1st NE Strawberry at Step: {s} (Day {s//24+1})")
                                return
        if done:
            break

check_apex34_ne_timing()
