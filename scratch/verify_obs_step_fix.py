import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1624303674})
env.reset()

obs0 = env.state[0].observation
print("Keys in Kaggle observation:", list(obs0.keys()))
print("Is 'step' in obs0?", "step" in obs0)
print("day:", obs0.get("day"), "hour:", obs0.get("hour"))

# Advance 5 steps
for _ in range(5):
    env.step([{"farmer": ["PASS"], "hands": [], "market": []}, {"farmer": ["PASS"], "hands": [], "market": []}])

obs5 = env.state[0].observation
print("\nAfter 5 steps:")
print("Is 'step' in obs5?", "step" in obs5)
print("day:", obs5.get("day"), "hour:", obs5.get("hour"))
print("Computed step:", obs5.get("day", 0) * 24 + obs5.get("hour", 0))
