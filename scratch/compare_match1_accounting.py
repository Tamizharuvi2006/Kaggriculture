import os, sys, json
import kaggle_environments

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json" # Match 1
hero_seat = 0

def compare_match1():
    import submission_rc12
    import submission_rc6_d1
    
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        
        sales = {}
        buys = {}
        hires = 0
        wages_paid = 0
        
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            act = mod.agent(obs)
            prices = obs["market"]["prices"]
            for o in act.get("market", []):
                if not o: continue
                if o[0] == "SELL":
                    sales[o[1]] = sales.get(o[1], 0) + o[2] * prices.get(o[1], 0) * 0.95
                elif o[0] in ["BUY_ANIMAL", "BUY_PRODUCT", "BUY_SEED"]:
                    item = o[1]
                    cost = o[2] * prices.get(item, 400 if item=="COW" else (500 if item=="SHEEP" else 20))
                    buys[item] = buys.get(item, 0) + cost
                elif o[0] == "HIRE":
                    hires += 1
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
                
        final_money = env.state[hero_seat].observation["farms"][hero_seat]["money"]
        print(f"\n==================== {name} (Final: ${final_money:,.0f}) ====================")
        print("Total Revenue: ${:,.0f}".format(sum(sales.values())))
        for k, v in sorted(sales.items(), key=lambda x: -x[1]):
            print(f"  + {k:<12}: ${v:>8,.0f}")
        print("Total Spending: ${:,.0f}".format(sum(buys.values())))
        for k, v in sorted(buys.items(), key=lambda x: -x[1]):
            print(f"  - {k:<12}: ${v:>8,.0f}")

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    compare_match1()
