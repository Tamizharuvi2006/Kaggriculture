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
    if hour == 0 and day % 2 == 0:
        farm = obs["farms"][0]
        tiles = farm["tiles"]
        crops = {}
        animals = 0
        for r in tiles:
            for t in r:
                if isinstance(t, dict):
                    if t.get("crop"): crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                    if t.get("animal"): animals += 1
        money = farm.get("money", 0)
        quads = len(farm.get("unlocked_quadrants", ["NW"]))
        print(f"D{day:02d} | Cash: ${money:,.0f} | Quads: {quads} | Animals: {animals} | Crops: {crops}")
    act = v3.agent(obs)
    env.step([act, opp_actions[s]])

print("Final Reward:", env.state[0].reward)
