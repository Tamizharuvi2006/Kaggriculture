"""Debug base agent actions on Day 29."""
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

# Step 696
obs0 = env.state[0].observation
a0 = sub_cand.agent(obs0, env.configuration)
a1 = sub_cand.agent(env.state[1].observation, env.configuration)
print("Step 696 act0:", a0)
env.step([a0, a1])

# Step 697
obs0_697 = env.state[0].observation
act_base_697 = sub_cand._base_agent(obs0_697)
act_cand_697 = sub_cand.agent(obs0_697, env.configuration)
print("\nStep 697 _base_agent returned:")
print("  farmer:", act_base_697.get("farmer"))
print("  hands:", act_base_697.get("hands"))
print("  market:", act_base_697.get("market"))
print("\nStep 697 candidate agent returned:")
print("  farmer:", act_cand_697.get("farmer"))
print("  hands:", act_cand_697.get("hands"))
print("  market:", act_cand_697.get("market"))
