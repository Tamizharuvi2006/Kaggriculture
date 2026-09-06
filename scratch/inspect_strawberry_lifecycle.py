import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(replay_path) as f:
    rep = json.load(f)

seed = rep["info"]["seed"]
steps = rep["steps"]
seat = 1
opp_actions = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

seed_purchases = []
straw_sales = []

for step in range(len(steps) - 1):
    if env.done: break
    obs = env.state[seat].observation
    day = obs.day
    hour = obs.hour
    p_straw = obs.market.prices.get("STRAWBERRY", 0)
    inv_straw = obs.market.inventory.get("STRAWBERRY", 0)
    
    act0 = opp_actions[step]
    act1 = rc2_mod.agent(env.state[1].observation)
    
    mkt = act1.get("market", []) if isinstance(act1, dict) else []
    for ord_item in mkt:
        if len(ord_item) >= 3:
            if ord_item[0] == "BUY_SEED":
                seed_purchases.append((day, hour, ord_item[1], ord_item[2]))
            elif ord_item[0] == "SELL" and ord_item[1] == "STRAWBERRY":
                straw_sales.append((day, hour, ord_item[2], p_straw, inv_straw))
                
    env.step([act0, act1])

print("=" * 80)
print("STRAWBERRY SEED PURCHASES ACROSS THE ENTIRE MATCH:")
print("=" * 80)
for p in seed_purchases:
    if p[2] == "STRAWBERRY":
        print(f"Day {p[0]:02d} Hour {p[1]:02d}: Bought {p[3]} STRAWBERRY seeds")

print("\n" + "=" * 80)
print("STRAWBERRY SALES ACROSS THE ENTIRE MATCH:")
print("=" * 80)
for s in straw_sales:
    print(f"Day {s[0]:02d} Hour {s[1]:02d}: Sold {s[2]} Strawberries at Price ${s[3]:.1f} (Market Inv: {s[4]:,})")
