import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import generalization_pipeline.submission_candidate_competitive_hybrid_v4 as v41
import json

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1002})
env.info = {"seed": 1002}
env.configuration["seed"] = 1002
env.reset()

snaps = {}

for s in range(320):
    o0 = env.state[0].observation
    o0["step"] = s
    a0 = v41.agent(o0)
    a1 = {"farmer": ["PASS"], "hands": [], "market": []}
    
    snaps[s] = {
        "step": s,
        "money": o0.farms[0]["money"],
        "shed": dict(o0.private["shed"]),
        "prices": dict(o0.market["prices"]),
        "inventory": dict(o0.market["inventory"]),
        "action": a0
    }
    
    env.step([a0, a1])

with open("fastsim/seed1002_off_trace.json", "w") as f:
    json.dump(snaps, f, indent=2)
print("Saved seed1002_off_trace.json")
