"""Inspect every step of Day 30 on Seed 1000 to see why Opponent gains $15.8k while D.1 gains only $8.5k."""
import os
import sys
import kaggle_environments
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1000})
env.reset()

print("Tracing Day 30 Step-by-Step on Seed 1000:")
while not env.done:
    step = env.state[0].observation.get("step", 0)

    obs0 = env.state[0].observation
    obs1 = env.state[1].observation

    act0 = sub_d1.agent(obs0, env.configuration)
    act1 = bot_v18_mod.agent(obs1)

    if step >= 695:
        f0 = obs0["farms"][0]
        f1 = obs1["farms"][1]
        c0 = float(f0.get("money", 0))
        c1 = float(f1.get("money", 0))
        w0 = len(f0.get("workers", []))
        w1 = len(f1.get("workers", []))

        print(f"Step {step:03d}: D.1 Cash=${c0:,.0f} (W={w0}, Mkt={act0.get('market', [])}) | Opp Cash=${c1:,.0f} (W={w1}, Mkt={act1.get('market', [])})")

    env.step([act0, act1])
