import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture")
import submission_rc12
sys.path.insert(0, r"D:\kaggriculture\scratch")
import candidate_rc15_v1

for name, mod in [("RC12", submission_rc12), ("RC15_v1", candidate_rc15_v1)]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    daily_money = {}
    daily_animals = {}
    daily_crops = {}
    daily_wheat_shed = {}
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        act = mod.agent(obs)
        env.step([act, opp_actions[s]])
        farm = env.state[hero_seat].observation["farms"][hero_seat]
        shed = env.state[hero_seat].observation["private"]["shed"]
        daily_money[day] = farm["money"]
        tiles = farm.get("tiles", [])
        daily_animals[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal"))
        daily_crops[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop"))
        daily_wheat_shed[day] = shed.get("WHEAT", 0)
    print(f"=== {name} Match 9 ===")
    print("Final Money:", env.state[hero_seat].observation["farms"][hero_seat]["money"])
    for d in [0, 5, 10, 15, 20, 24, 25, 26, 27, 28, 29]:
        print(f"  Day {d:02d}: Money={daily_money.get(d, 0):>6.0f}, Animals={daily_animals.get(d, 0)}, Crops={daily_crops.get(d, 0)}, WheatShed={daily_wheat_shed.get(d, 0)}")
