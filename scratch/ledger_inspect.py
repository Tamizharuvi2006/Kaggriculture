import os, sys, json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json" # Match 1
hero_seat = 0

def ledger_inspect():
    import submission_rc12
    import submission_rc6_d1
    
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        sales = {}
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            act = mod.agent(obs)
            prices = obs["market"]["prices"]
            for o in act.get("market", []):
                if o and o[0] == "SELL":
                    item = o[1]
                    qty = o[2]
                    p = prices.get(item, 0)
                    sales[item] = sales.get(item, 0) + qty * p * 0.95
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
        print(f"\n[{name}] Total Score: ${env.state[hero_seat].observation['farms'][hero_seat]['money']:,}")
        for item, val in sorted(sales.items(), key=lambda x: -x[1]):
            print(f"  {item:<12}: ${val:>8,.0f}")

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    ledger_inspect()
