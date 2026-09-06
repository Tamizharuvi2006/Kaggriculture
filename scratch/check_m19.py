import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95773643\episode-95773643-replay.json"
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
    fert_sold = 0
    milk_sold = 0
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        act = mod.agent(obs)
        for o in act.get("market", []):
            if o and o[0] == "SELL":
                p = obs["market"]["prices"].get(o[1], 0)
                if o[1] == "FERTILIZER": fert_sold += o[2] * p * 0.95
                elif o[1] == "MILK": milk_sold += o[2] * p * 0.95
        env.step([act, opp_actions[s]])
        farm = env.state[hero_seat].observation["farms"][hero_seat]
        daily_money[day] = farm["money"]
    print(f"=== {name} Match 19 ===")
    print("Final Money:", env.state[hero_seat].observation["farms"][hero_seat]["money"])
    print(f"Fertilizer Revenue: ${fert_sold:,.0f}")
    print(f"Milk Revenue:       ${milk_sold:,.0f}")
    for d in [5, 10, 15, 20, 25, 29]:
        print(f"  Day {d:02d}: Money={daily_money.get(d, 0):>6.0f}")
