"""Inspect observation structure in kaggriculture."""
import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 10, "seed": 42})
env.reset()
obs0 = env.state[0].observation
print("Observation keys:", list(obs0.keys()) if isinstance(obs0, dict) else dir(obs0))
if isinstance(obs0, dict):
    for k, v in obs0.items():
        print(f"  {k}: type={type(v)}, len={len(v) if hasattr(v, '__len__') else v}")
