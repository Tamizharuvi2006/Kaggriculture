import os
import sys
import importlib.util
import numpy as np
import kaggle_environments

v41_path = r"D:\kagriulture\Kaggriculture\baseline\kaitofukami-v18.py"
apex34_path = r"D:\kagriulture\Kaggriculture\generalization_pipeline\submission_candidate_apex34.py"

def load(path):
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "agent")

apex_fn = load(apex34_path)
v41_fn = load(v41_path)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": 504110})

obs = env.reset()

for s in range(720):
    obs0 = env.state[0]["observation"]
    obs1 = env.state[1]["observation"]
    
    act0 = apex_fn(obs0)
    act1 = v41_fn(obs1)
    
    farm0 = obs0.get("farms", [{}])[0]
    farm1 = obs1.get("farms", [{}])[0]
    
    c0 = float(farm0.get("money", 0.0) or 0.0)
    c1 = float(farm1.get("money", 0.0) or 0.0)
    q0 = len(farm0.get("unlocked_quadrants", []))
    q1 = len(farm1.get("unlocked_quadrants", []))
    
    if s % 48 == 0 or s in (71, 72, 96, 120, 360, 480, 600, 719):
        print(f"Step {s:3d} (Day {s//24+1:2d}): P0 Cash: ${c0:8,.1f} (Q={q0}) | P1 Cash: ${c1:8,.1f} (Q={q1}) | Delta: ${c0-c1:+8,.1f}")

    env.step([act0, act1])
    if env.done:
        break

w0 = float(env.state[0]["observation"]["farms"][0]["money"])
w1 = float(env.state[1]["observation"]["farms"][0]["money"])
print(f"\nFinal Outcome on Seed 504110: P0 = ${w0:,.1f} vs P1 = ${w1:,.1f} | Delta = ${w0-w1:+,.1f}")
