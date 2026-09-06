import os, sys, json
import kaggle_environments

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json" # Match 14
hero_seat = 0

def straw_audit():
    import submission_rc12
    import submission_rc6_d1
    
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        harvests = 0
        straw_sold = 0
        waters = 0
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            act = mod.agent(obs)
            # Count HARVEST actions
            for h in act.get("hands", []) + [act.get("farmer")]:
                if h and len(h) > 2 and h[0] == "HARVEST":
                    harvests += 1
                elif h and len(h) > 2 and h[0] == "WATER":
                    waters += 1
            for o in act.get("market", []):
                if o and o[0] == "SELL" and o[1] == "STRAWBERRY":
                    straw_sold += o[2]
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
        print(f"[{name}] Total Strawberry Harvests: {harvests} | Units Sold: {straw_sold} | Waters: {waters}")

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    straw_audit()
