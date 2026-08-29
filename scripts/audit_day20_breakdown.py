"""Audit script to track the exact collapse from Day 20 to Day 30 on Seed 1000."""
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

print("Tracking Day 20 to 30 Evolution on Seed 1000:")
while not env.done:
    step = env.state[0].observation.get("step", 0)
    day = (step // 24) + 1
    hour = step % 24

    obs0 = env.state[0].observation
    obs1 = env.state[1].observation

    act0 = sub_d1.agent(obs0, env.configuration)
    act1 = bot_v18_mod.agent(obs1)

    if step in [456, 576, 624, 672, 696, 719]:
        f0 = obs0["farms"][0]
        f1 = obs1["farms"][1]
        mkt = obs0.get("market", {})
        prices = mkt.get("prices", mkt.get("current_prices", {}))

        p0_ripe = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("stage") == 3)
        p1_ripe = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("stage") == 3)

        p0_shed_s = int(obs0.get("private", {}).get("shed", {}).get("STRAWBERRY", 0))
        p0_shed_m = int(obs0.get("private", {}).get("shed", {}).get("MILK", 0))

        p0_w = len(f0.get("workers", []))
        p1_w = len(f1.get("workers", []))

        print(f"Day {day:02d} H{hour:02d} (Step {step:03d}):")
        print(f"  P0 (D.1): Cash=${f0.get('money', 0):,.0f} | Workers={p0_w} | Shed(Straw={p0_shed_s}, Milk={p0_shed_m}) | Field Ripe={p0_ripe}")
        print(f"  P1 (Opp): Cash=${f1.get('money', 0):,.0f} | Workers={p1_w} | Field Ripe={p1_ripe}")
        print(f"  Prices  : Straw=${prices.get('STRAWBERRY', 0):.1f} | Milk=${prices.get('MILK', 0):.1f} | Wheat=${prices.get('WHEAT', 0):.1f}")
        print("-" * 80)

    env.step([act0, act1])

r0 = float(env.state[0].reward or 0.0)
r1 = float(env.state[1].reward or 0.0)
print(f"FINAL TERMINAL RESULT: D.1=${r0:,.0f} vs Opp=${r1:,.0f} | Margin=${r0-r1:+,.0f}")
