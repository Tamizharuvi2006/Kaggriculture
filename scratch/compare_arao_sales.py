import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_h6_threshold16 as h6_mod

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(path_arao) as f: rep_arao = json.load(f)
steps = rep_arao["steps"]
tape_s0 = {s: (steps[s+1][0]["action"], None) for s in range(len(steps)-1)}

def run_agent_trace(agent_mod):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep_arao["info"]["seed"]})
    env.reset()
    
    sales_by_item = {}
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[1].observation
        act0 = tape_s0[s][0]
        act1 = agent_mod.agent(obs)
        
        if isinstance(act1, dict):
            for ord_item in act1.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = obs.market.prices.get(item, 0)
                    r = qty * price * 0.95
                    sales_by_item[item] = sales_by_item.get(item, 0.0) + r
                    
        env.step([act0, act1])
        
    return env.state[1].observation.farms[1].money, sales_by_item

score_rc2, sales_rc2 = run_agent_trace(rc2_mod)
score_h6, sales_h6 = run_agent_trace(h6_mod)

print("=" * 70)
print(f"ARAO SEAT 1 COMPARISON: RC2 vs H6-THRESHOLD16")
print("=" * 70)
print(f"RC2 Final Score: ${score_rc2:,.0f}")
print(f"H6  Final Score: ${score_h6:,.0f} (Diff: ${score_h6 - score_rc2:+,.0f})")
print("\nSales Breakdown:")
all_items = set(list(sales_rc2.keys()) + list(sales_h6.keys()))
for it in sorted(all_items):
    r_rc2 = sales_rc2.get(it, 0.0)
    r_h6 = sales_h6.get(it, 0.0)
    print(f"  {it:<15} | RC2: ${r_rc2:>9,.0f} | H6: ${r_h6:>9,.0f} | Diff: ${r_h6 - r_rc2:>+9,.0f}")
