"""Print farm dictionary keys."""
import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 10, "seed": 42})
env.reset()
obs0 = env.state[0].observation
farm0 = obs0["farms"][0]
print("Farm keys:", list(farm0.keys()))
for k, v in farm0.items():
    print(f"  {k}: {v}")
