import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14"),
]

def detailed_trace(mod_name, rp, seat):
    if mod_name in sys.modules: del sys.modules[mod_name]
    mod = __import__(mod_name)
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    trace = []
    prev_d = -1
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[seat].observation
        d = obs["day"]
        act = mod.agent(obs)
        if d != prev_d:
            farm = obs["farms"][seat]
            shed = obs["private"]["shed"]
            p = obs["market"]["prices"]
            trace.append({
                "day": d,
                "money": farm["money"],
                "straw_rev": mod._MATCH_LEDGER.get("strawberry_revenue", 0) if hasattr(mod, "_MATCH_LEDGER") else 0,
                "milk_rev": mod._MATCH_LEDGER.get("milk_revenue", 0) if hasattr(mod, "_MATCH_LEDGER") else 0,
                "shed_w": shed.get("WHEAT", 0),
                "shed_fert": shed.get("FERTILIZER", 0),
                "p_straw": p.get("STRAWBERRY"),
                "p_milk": p.get("MILK"),
            })
            prev_d = d
        if seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
    final_score = int(env.state[seat].observation["farms"][seat]["money"])
    return final_score, trace

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    for rp, seat, label in replays:
        print(f"\n==================== {label} ====================")
        s12, t12 = detailed_trace("submission_rc12", rp, seat)
        s6, t6 = detailed_trace("submission_rc6_d1", rp, seat)
        print(f"RC12 Score: ${s12:,} | RC6_D1 Score: ${s6:,}")
        print("Day | RC12: Money / ShedW / P_Straw / P_Milk | RC6: Money / ShedW / P_Straw / P_Milk")
        for d in range(11, 25):
            r12 = t12[d]
            r6 = t6[d]
            print(f"D{d:02d} | ${r12['money']:>6,.0f} / {r12['shed_w']:>2d}w / ${r12['p_straw']:>3} / ${r12['p_milk']:>3} | ${r6['money']:>6,.0f} / {r6['shed_w']:>2d}w / ${r6['p_straw']:>3} / ${r6['p_milk']:>3}")
