import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments, json
import economic_brain_v2.submission_adaptive_v3_economic as v3

replay_file = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(replay_file) as f: rep = json.load(f)
opp_actions = [frame[1].get("action") for frame in rep["steps"][1:]]
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": rep["info"]["seed"]})
env.reset()

revenue = {}
units = {}

for s in range(len(opp_actions)):
    if env.done: break
    obs = env.state[0].observation
    prices = obs["market"]["prices"]
    act = v3.agent(obs)
    for m in act.get("market", []):
        if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
            item = m[1]
            q = m[2]
            p = float(prices.get(item, 0)) * 0.95
            revenue[item] = revenue.get(item, 0.0) + q * p
            units[item] = units.get(item, 0) + q
    env.step([act, opp_actions[s]])

print("V3 Match 1 Sales Breakdown:")
for item, rev in sorted(revenue.items(), key=lambda x: x[1], reverse=True):
    print(f"  {item:<12}: {units[item]:>4} units -> ${rev:>8,.0f}")
print(f"Total Gross Sales: ${sum(revenue.values()):,.0f}")
print(f"Final Reward: ${env.state[0].reward:,.0f}")
