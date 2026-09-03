import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments, json
import economic_brain_v2.submission_adaptive_v3_economic as v3

replay_file = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(replay_file) as f: rep = json.load(f)
opp_actions = [frame[1].get("action") for frame in rep["steps"][1:]]
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": rep["info"]["seed"]})
env.reset()

for s in range(len(opp_actions)):
    if env.done: break
    obs = env.state[0].observation
    day = s // 24
    hour = s % 24
    act = v3.agent(obs)
    for m in act.get("market", []):
        if isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_ANIMAL":
            money = obs["farms"][0]["money"]
            print(f"D{day:02d}:H{hour:02d} Bought {m[1]}: {m[2]} | Cash: ${money:,.0f}")
    env.step([act, opp_actions[s]])
