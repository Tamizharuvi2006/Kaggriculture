import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14"),
]

def feed_inspect(rp, seat, label):
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc6_d1
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    wheat_bought = 0
    wheat_bought_cost = 0
    starvations = 0
    unfed = 0
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[seat].observation
        act = submission_rc6_d1.agent(obs)
        prices = obs["market"]["prices"]
        for o in act.get("market", []):
            if o and o[0] == "BUY_PRODUCT" and o[1] == "WHEAT":
                wheat_bought += o[2]
                wheat_bought_cost += o[2] * prices.get("WHEAT", 20)
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
            
    print(f"\n[{label}] Total Wheat Bought from Town: {wheat_bought} units, Cost: ${wheat_bought_cost:,.0f}")

for rp, seat, label in replays:
    hero_seat = seat
    feed_inspect(rp, seat, label)
