import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments, json
import candidates.submission_adaptive_v2_economic as cand

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
    farm = obs["farms"][0]
    act = cand.agent(obs)
    if 5 <= day <= 7 and hour <= 3:
        mkt = act.get("market", [])
        print(f"D{day:02d}:H{hour:02d} | Money: ${farm['money']:,.0f} | HiresToday: {farm.get('hires_today')} | Hands: {len(farm.get('hands', []))} | Mkt: {mkt}")
    env.step([act, opp_actions[s]])
