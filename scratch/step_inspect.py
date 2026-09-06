import os, sys, json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json"
hero_seat = 0

def run_compare():
    import submission_rc12
    import submission_rc6_d1
    
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            day = obs["day"]
            act = mod.agent(obs)
            if day == 11 and (act.get("market") or act.get("hires")):
                print(f"[{name}] Step {s} (Day {day}): market={act.get('market')} hires={act.get('hires')}")
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
        print(f"[{name}] Final money: {env.state[hero_seat].observation['farms'][hero_seat]['money']}")

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    run_compare()
