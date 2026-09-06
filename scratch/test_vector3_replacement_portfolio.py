import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
from concurrent.futures import ProcessPoolExecutor
import kaggle_environments

targets = [
    ("Soumi Ghosh (Extreme Flooder)", r"reports/live_match_telemetry/episode-104388418-replay.json", 1),
    ("Soumi Ghosh S0",                r"reports/live_match_telemetry/episode-104388418-replay.json", 0),
    ("RicardoLopez S1",               r"reports/live_match_telemetry/episode-104475527-replay.json", 1),
    ("RicardoLopez S0",               r"reports/live_match_telemetry/episode-104475527-replay.json", 0),
    ("ayman elamin S1",               r"reports/live_match_telemetry/episode-104433117-replay.json", 1),
    ("arao (Passive Holder)",         r"reports/live_match_telemetry/episode-104379472-replay.json", 1),
    ("High Ceiling (Seed 628719714)", None, 1),
]

def run_portfolio_sim(args):
    label, r_path, seat, portfolio_mode = args
    import submission_rc4_1_clean as rc41_mod
    
    if r_path:
        p = os.path.join(r"D:\kaggriculture", r_path)
        with open(p) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = 628719714
        opp_actions = None
        max_steps = 720
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    straw_rev = 0.0
    carrot_rev = 0.0
    wheat_rev = 0.0
    milk_wool_rev = 0.0
    wheat_bought_cost = 0.0
    
    confirm_day = None
    confirm_hour = None
    
    orig_crop_plan = rc41_mod._crop_plan
    
    def custom_crop_plan(day):
        plan = orig_crop_plan(day)
        # Apply only after flood confirmed
        if getattr(rc41_mod, "_FLOOD_CONFIRMED", False) and day >= 11:
            # Find the non-wheat, non-animal, non-strawberry plots (the flexible buffer plots)
            flex_plots = [pos for pos, c in plan.items() if c not in ("WHEAT", "STRAWBERRY")]
            if len(flex_plots) >= 2:
                if portfolio_mode == "2-carrots":
                    plan[flex_plots[0]] = "CARROT"
                    plan[flex_plots[1]] = "CARROT"
                elif portfolio_mode == "1-carrot-1-wheat":
                    plan[flex_plots[0]] = "CARROT"
                    plan[flex_plots[1]] = "WHEAT"
                elif portfolio_mode == "2-wheat":
                    plan[flex_plots[0]] = "WHEAT"
                    plan[flex_plots[1]] = "WHEAT"
        return plan

    rc41_mod._crop_plan = custom_crop_plan
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        
        act_bot = rc41_mod.agent(obs)
        
        if r_path:
            opp_act = opp_actions[step]
        else:
            opp_act = rc41_mod.agent(env.state[1 - seat].observation)
        acts = [opp_act, act_bot] if seat == 1 else [act_bot, opp_act]
        
        if getattr(rc41_mod, "_FLOOD_CONFIRMED", False) and confirm_day is None:
            confirm_day = getattr(rc41_mod, "_FLOOD_CONFIRMED_DAY", day)
            confirm_hour = hour
            
        if isinstance(act_bot, dict):
            for ord_item in act_bot.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY": straw_rev += r
                    elif item == "CARROT": carrot_rev += r
                    elif item == "WHEAT": wheat_rev += r
                    elif item in ("MILK", "WOOL"): milk_wool_rev += r
                elif len(ord_item) >= 3 and ord_item[0] == "BUY_PRODUCT" and ord_item[1] == "WHEAT":
                    qty = ord_item[2]
                    price = mkt.prices.get("WHEAT", 25)
                    wheat_bought_cost += qty * price
                    
        env.step(acts)
        
    rc41_mod._crop_plan = orig_crop_plan
    score = env.state[seat].observation.farms[seat].money
    return {
        "label": label,
        "seat": seat,
        "mode": portfolio_mode,
        "score": score,
        "confirm_day": confirm_day,
        "confirm_hour": confirm_hour,
        "straw_rev": straw_rev,
        "carrot_rev": carrot_rev,
        "wheat_rev": wheat_rev,
        "milk_wool_rev": milk_wool_rev,
        "wheat_bought_cost": wheat_bought_cost
    }

if __name__ == "__main__":
    sweep_tasks = []
    for label, r_path, seat in targets:
        for mode in ("2-carrots", "1-carrot-1-wheat", "2-wheat"):
            sweep_tasks.append((label, r_path, seat, mode))
            
    print("=" * 140)
    print("PHASE 15: VECTOR 3 REPLACEMENT PORTFOLIO EXPERIMENT (2 CARROTS vs 1 CARROT + 1 WHEAT vs 2 WHEAT)")
    print("=" * 140)
    print(f"{'REGIME':<30} | {'MODE':<16} | {'SCORE':>10} | {'DIFF(vs 2C)':>11} | {'CARROT $':>9} | {'WHEAT $':>8} | {'MILK/WOOL':>10} | {'FEED BOUGHT':>11}")
    print("-" * 140)
    sys.stdout.flush()
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_portfolio_sim, sweep_tasks))
        
    by_regime = {}
    for r in results:
        by_regime.setdefault(r["label"], {})[r["mode"]] = r
        
    for label, m_dict in by_regime.items():
        base_score = m_dict["2-carrots"]["score"]
        for mode in ("2-carrots", "1-carrot-1-wheat", "2-wheat"):
            r = m_dict[mode]
            diff = r["score"] - base_score
            print(f"{label:<30} | {mode:<16} | ${r['score']:>9,.0f} | ${diff:>+10,.0f} | ${r['carrot_rev']:>8,.0f} | ${r['wheat_rev']:>7,.0f} | ${r['milk_wool_rev']:>9,.0f} | ${r['wheat_bought_cost']:>10,.0f}")
        print("-" * 140)
        sys.stdout.flush()
        
    print("=" * 140)
