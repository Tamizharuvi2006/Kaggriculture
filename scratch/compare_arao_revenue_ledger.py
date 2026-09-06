import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42
import submission_rc5_a_early_pasture as rc5a

path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]
opp_actions = [steps[s][0].get("action") for s in range(1, len(steps))]

def get_ledger(agent_mod):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    sales = Counter()
    purchases = Counter()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[1].observation
        act = agent_mod.agent(obs)
        if isinstance(act, dict):
            for m in act.get("market", []):
                if m and len(m) >= 3:
                    if m[0] == "SELL":
                        sales[m[1]] += m[2]
                    elif m[0] == "BUY_SEED":
                        purchases[m[1]] += m[2]
                    elif m[0] == "BUY_PRODUCT":
                        purchases[m[1]] += m[2]
                elif m and m[0] == "BUY_LAND":
                    purchases["LAND"] += 1
                elif m and m[0] == "HIRE":
                    purchases["HIRE"] += 1
        env.step([opp_actions[s], act])
    f = env.state[1].observation["farms"][1]
    return f["money"], sales, purchases, agent_mod._MATCH_LEDGER

m42, s42, p42, led42 = get_ledger(rc42)
m5a, s5a, p5a, led5a = get_ledger(rc5a)

print("=" * 80)
print(f"ARAO PASSIVE LEDGER COMPARISON: RC4.2 (${m42:,.0f}) vs RC5-A (${m5a:,.0f})")
print("=" * 80)
print(f"{'ITEM / CATEGORY':<25} | {'RC4.2 (Control)':<20} | {'RC5-A (Early Pasture)':<20} | {'DELTA':<15}")
print("-" * 80)
for k in sorted(list(set(list(led42.keys()) + list(led5a.keys())))):
    val42 = led42[k]
    val5a = led5a[k]
    delta = val5a - val42
    if isinstance(val42, float) or isinstance(val5a, float):
        print(f"{k:<25} | ${val42:>15,.0f} | ${val5a:>15,.0f} | ${delta:>+12,.0f}")
    else:
        print(f"{k:<25} | {val42:>16} | {val5a:>16} | {delta:>+12}")
print("=" * 80)
