import os, sys, json
import kaggle_environments

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json" # Match 1
hero_seat = 0

def check_straw_water():
    import submission_rc12
    import submission_rc6_d1
    
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        daily_waters = [0] * 30
        daily_harvests = [0] * 30
        
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            d = obs["day"]
            act = mod.agent(obs)
            all_unit_actions = act.get("hands", []) + [act.get("farmer")]
            for a in all_unit_actions:
                if a and len(a) > 2:
                    if a[0] == "WATER":
                        daily_waters[d] += 1
                    elif a[0] == "HARVEST":
                        daily_harvests[d] += 1
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
        print(f"\n[{name}]")
        print("Daily Strawberry Waters (Days 11-25):", daily_waters[11:26], "Total:", sum(daily_waters[11:26]))
        print("Daily Strawberry Harvests (Days 11-25):", daily_harvests[11:26], "Total:", sum(daily_harvests[11:26]))

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    check_straw_water()
