"""Trace step-by-step observation differences between Seed 66666 (Elite) and Seed 90909 (Crash) on Steps 1-120."""
import os
import sys
import kaggle_environments

env_elite = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 66666})
env_elite.reset()

env_crash = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 90909})
env_crash.reset()

for step in range(121):
    obs_e = env_elite.state[0].observation
    obs_c = env_crash.state[0].observation

    if step in (24, 48, 72, 96, 120):
        p_e_straw = obs_e.get("market", {}).get("prices", {}).get("STRAWBERRY")
        p_c_straw = obs_c.get("market", {}).get("prices", {}).get("STRAWBERRY")
        p_e_milk = obs_e.get("market", {}).get("prices", {}).get("MILK")
        p_c_milk = obs_c.get("market", {}).get("prices", {}).get("MILK")
        shops_e = obs_e.get("town", {}).get("unlocked_shops", [])
        shops_c = obs_c.get("town", {}).get("unlocked_shops", [])
        
        print(f"Step {step:03d} (Day {step//24}) | Elite: Straw=${p_e_straw}, Milk=${p_e_milk}, Shops={shops_e} | Crash: Straw=${p_c_straw}, Milk=${p_c_milk}, Shops={shops_c}")

    env_elite.step([{"farmer": ["PASS"], "market": []}, {"farmer": ["PASS"], "market": []}])
    env_crash.step([{"farmer": ["PASS"], "market": []}, {"farmer": ["PASS"], "market": []}])
