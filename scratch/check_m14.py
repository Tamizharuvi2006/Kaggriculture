import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture")
import submission_rc6_d1
import submission_rc12

for name, mod in [("RC6_D1", submission_rc6_d1), ("RC12", submission_rc12)]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    daily_money = {}
    daily_animals = {}
    daily_cows = {}
    daily_sheep = {}
    buys = []
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        act = mod.agent(obs)
        for o in act.get("market", []):
            if o and o[0] == "BUY_ANIMAL":
                buys.append((day, o[1], o[2]))
        env.step([act, opp_actions[s]])
        farm = env.state[hero_seat].observation["farms"][hero_seat]
        daily_money[day] = farm["money"]
        tiles = farm.get("tiles", [])
        daily_cows[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
        daily_sheep[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    print(f"=== {name} Match 14 ===")
    print("Final Money:", env.state[hero_seat].observation["farms"][hero_seat]["money"])
    print("Animal Buys:", buys)
    for d in [5, 9, 10, 11, 12, 13, 14, 15, 20, 25, 29]:
        print(f"  Day {d:02d}: Money={daily_money.get(d, 0):>6.0f}, Cows={daily_cows.get(d, 0)}, Sheep={daily_sheep.get(d, 0)}")
