import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments
import submission_challenger_exp208 as old_mod
import submission_challenger_exp208_clean as new_mod

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()

obs0 = env.state[0].observation
act_old = old_mod.agent(obs0)
act_new = new_mod.agent(obs0)

print("ACT OLD:", act_old)
print("ACT NEW:", act_new)
print("EQUAL?", act_old == act_new)
