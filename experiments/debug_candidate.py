"""Debug candidate agent at step 696."""
import os, sys, importlib.util
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

spec_cand = importlib.util.spec_from_file_location("sub_cand", os.path.join(BASE_DIR, "candidate_adaptive_terminal.py"))
sub_cand = importlib.util.module_from_spec(spec_cand)
spec_cand.loader.exec_module(sub_cand)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1000})
env.reset()
while env.state[0].observation.get("step", 0) <= 695:
    a0 = sub_cand.agent(env.state[0].observation, env.configuration)
    a1 = sub_cand.agent(env.state[1].observation, env.configuration)
    env.step([a0, a1])

obs0_696 = env.state[0].observation
act0_696 = sub_cand.agent(obs0_696, env.configuration)
print("Step 696 Observation step:", obs0_696.get("step"))
print("Step 696 Returned Action:", act0_696)
