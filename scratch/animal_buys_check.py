import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95622859\episode-95622859-replay.json", 0, "Match 17"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95775674\episode-95775674-replay.json", 0, "Match 20"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1"),
]

def run_compare():
    import submission_rc6_d1
    import submission_rc12
    
    for rp, hero_seat, label in replays:
        print(f"\n==================== {label} ====================")
        with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
        steps = rep["steps"]
        opp_seat = 1 - hero_seat
        opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
        
        for mod, name in [(submission_rc6_d1, "RC6_D1"), (submission_rc12, "RC12")]:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
            env.reset()
            for s in range(len(steps)-1):
                if env.done: break
                obs = env.state[hero_seat].observation
                day = obs["day"]
                act = mod.agent(obs)
                for o in act.get("market", []):
                    if o and "ANIMAL" in o[0]:
                        print(f"[{name}] Day {day} Step {s}: {o}")
                if hero_seat == 0:
                    env.step([act, opp_actions[s]])
                else:
                    env.step([opp_actions[s], act])
            print(f"[{name}] Final money: {env.state[hero_seat].observation['farms'][hero_seat]['money']}")

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    run_compare()
