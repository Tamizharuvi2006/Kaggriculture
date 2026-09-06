import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
from concurrent.futures import ProcessPoolExecutor
import kaggle_environments

replays = [
    ("episode-104475527-replay.json", "RicardoLopez (1052 Elo)"),
    ("episode-104424149-replay.json", "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", "Soumi Ghosh"),
    ("episode-104379472-replay.json", "arao"),
]

low_seeds = [
    (628719714, "Ep 105112452 ($29k Floor)"),
    (334330253, "Ep 105105439 ($38k vs zZx Hee)"),
    (652661405, "Ep 105107201 ($46k vs 623 Elo)"),
    (264913612, "Ep 105116829 ($57k)"),
    (1064891062, "Ep 105104584 ($73k vs 113k)"),
]

def run_single_sim(args):
    label, r_path, s_val, seat, persistence_mode = args
    import submission_rc2_terminal_horizon as rc2_mod
    
    if r_path:
        with open(r_path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = s_val
        opp_actions = None
        max_steps = 720
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    potential_risk = False
    flood_confirmed = False
    confirm_day = None
    confirm_hour = None
    
    prev_inv = 10000
    elevated_hours_count = 0
    straw_rev_pre = 0.0
    other_rev = 0.0
    
    orig_crop_plan = rc2_mod._crop_plan
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        delta_inv = inv_straw - prev_inv
        prev_inv = inv_straw
        
        # Stage 1: Day 11 Hour 0 Forecast
        if day == 11 and hour == 0:
            opp_farm = obs.farms[1 - seat]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True
                
        # Stage 3: Realized Market Inventory Persistence Logic (Day 15+)
        if potential_risk and day >= 15 and not flood_confirmed:
            if persistence_mode == "1-tick":
                if inv_straw >= 9935 and delta_inv > 0:
                    flood_confirmed = True
                    confirm_day = day
                    confirm_hour = hour
            elif persistence_mode == "2-hours":
                if inv_straw >= 9935:
                    elevated_hours_count += 1
                    if elevated_hours_count >= 2:
                        flood_confirmed = True
                        confirm_day = day
                        confirm_hour = hour
                else:
                    elevated_hours_count = 0
                    
        # Policy C Adaptive Allocation
        if potential_risk and day >= 11:
            quota = 10 if flood_confirmed else 24
            rc2_mod._crop_plan = lambda d: {
                pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                for i, (pos, c) in enumerate(orig_crop_plan(d).items())
            }
        else:
            rc2_mod._crop_plan = orig_crop_plan
            
        try:
            act_bot = rc2_mod.agent(obs)
            if r_path:
                opp_act = opp_actions[step]
            else:
                opp_act = rc2_mod.agent(env.state[1 - seat].observation)
            acts = [opp_act, act_bot] if seat == 1 else [act_bot, opp_act]
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        if isinstance(act_bot, dict):
            for ord_item in act_bot.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY":
                        if not flood_confirmed:
                            straw_rev_pre += r
                    else:
                        other_rev += r
                        
        env.step(acts)
        
    score = env.state[seat].observation.farms[seat].money
    return {
        "label": label,
        "seat": seat,
        "mode": persistence_mode,
        "score": score,
        "confirm_day": confirm_day,
        "confirm_hour": confirm_hour,
        "straw_rev_pre": straw_rev_pre,
        "other_rev": other_rev
    }

def run_paired_match(match_args):
    label, r_path, s_val, seat = match_args
    res1 = run_single_sim((label, r_path, s_val, seat, "1-tick"))
    res2 = run_single_sim((label, r_path, s_val, seat, "2-hours"))
    return res1, res2

if __name__ == "__main__":
    match_tasks = []
    for r_name, opp_label in replays:
        p = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
        for seat in (0, 1):
            match_tasks.append((opp_label, p, None, seat))
            
    for s_val, label in low_seeds:
        for seat in (0, 1):
            match_tasks.append((label, None, s_val, seat))
            
    print("=" * 125)
    print("PHASE 15: VECTOR 1 CONFIRMATION PERSISTENCE (10 PARALLEL WORKERS, 20 MATCHES)")
    print("=" * 125)
    print(f"{'MATCH / OPPONENT':<28} | {'SEAT':<4} | {'1-TICK SCORE':>12} | {'2-HR SCORE':>12} | {'DELTA':>10} | {'1-TICK CONF':>11} | {'2-HR CONF':>11}")
    print("-" * 125)
    sys.stdout.flush()
    
    diffs = []
    with ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_paired_match, match_tasks))
        
    for r1, r2 in results:
        d = r2["score"] - r1["score"]
        diffs.append(d)
        c1_str = f"D{r1['confirm_day']} H{r1['confirm_hour']}" if r1['confirm_day'] else "NO"
        c2_str = f"D{r2['confirm_day']} H{r2['confirm_hour']}" if r2['confirm_day'] else "NO"
        print(f"{r1['label']:<28} | S{r1['seat']}  | ${r1['score']:>11,.0f} | ${r2['score']:>11,.0f} | ${d:>+9,.0f} | {c1_str:>11} | {c2_str:>11}")
        sys.stdout.flush()
        
    print("=" * 125)
    print(f"Total Matches: {len(diffs)} | Identical Matches: {sum(1 for x in diffs if x == 0)}/20 | Mean Delta: ${sum(diffs)/len(diffs):>+,.2f}")
    print("=" * 125)
    sys.stdout.flush()
