import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments
import submission_rc2_terminal_horizon as rc2

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 628719714})
env.reset()

for s in range(11 * 24 + 1):
    act0 = rc2.agent(env.state[0].observation)
    act1 = rc2.agent(env.state[1].observation)
    env.step([act0, act1])

obs = env.state[0].observation
plan = rc2._crop_plan(11)

counts = {}
for pos, crop in plan.items():
    counts[crop] = counts.get(crop, 0) + 1

print("RC2 Crop Plan at Day 11 on Seed 628719714:")
print(counts)
