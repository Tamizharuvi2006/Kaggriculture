import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture")
import submission_rc12
sys.path.insert(0, r"D:\kaggriculture\scratch")
import candidate_rc15_fert_boost

for name, mod in [("RC12", submission_rc12), ("FertBoost", candidate_rc15_fert_boost)]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    daily_money = {}
    daily_animals = {}
    daily_straw_sales = {}
    daily_milk_sales = {}
    unfed_days = []
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        farm = obs["farms"][hero_seat]
        act = mod.agent(obs)
        for o in act.get("market", []):
            if o and o[0] == "SELL":
                p = obs["market"]["prices"].get(o[1], 0)
                if o[1] == "STRAWBERRY": daily_straw_sales[day] = daily_straw_sales.get(day, 0) + o[2] * p * 0.95
                elif o[1] == "MILK": daily_milk_sales[day] = daily_milk_sales.get(day, 0) + o[2] * p * 0.95
        env.step([act, opp_actions[s]])
        daily_money[day] = farm["money"]
        tiles = farm.get("tiles", [])
        daily_animals[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal"))
        unfed = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") and t.get("consecutive_unfed", 0) > 0)
        if unfed > 0 and hour == 0 and day not in unfed_days:
            unfed_days.append(day)
    print(f"=== {name} Match 1 ===")
    print("Final Money:", env.state[hero_seat].observation["farms"][hero_seat]["money"])
    print("Unfed Days:", unfed_days)
    print(f"Total Straw Sales: ${sum(daily_straw_sales.values()):,.0f}")
    print(f"Total Milk Sales:  ${sum(daily_milk_sales.values()):,.0f}")
    for d in [5, 10, 15, 20, 24, 25, 26, 27, 28, 29]:
        print(f"  Day {d:02d}: Money={daily_money.get(d, 0):>6.0f}, Animals={daily_animals.get(d, 0)}")
