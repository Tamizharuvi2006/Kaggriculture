"""Probe script to inspect Step 500-600 price, inventory, and order mechanics."""
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

print("Tracking Step 530-580 on Seed 1000:")
while not env.done:
    step = env.state[0].observation.get("step", 0)
    day = (step // 24) + 1
    hour = step % 24

    obs0 = env.state[0].observation
    mkt = obs0.get("market", {})
    prices = mkt.get("prices", mkt.get("current_prices", {}))
    p_straw = float(prices.get("STRAWBERRY", 0))

    priv = obs0.get("private", {})
    shed = priv.get("shed", {})
    straw_shed = int(shed.get("STRAWBERRY", 0))

    act0 = sub_d1.agent(obs0, env.configuration)
    a_opp = bot_v18_mod.agent(env.state[1].observation)

    if 530 <= step <= 580 and (straw_shed > 0 or act0.get("market")):
        print(f"Step {step:03d} (Day {day:02d} H{hour:02d}): P_Straw=${p_straw:.1f} | Shed_Straw={straw_shed} | Act={act0.get('market', [])}")

    env.step([act0, a_opp])
