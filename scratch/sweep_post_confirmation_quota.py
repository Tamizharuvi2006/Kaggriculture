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

def run_quota_sim(args):
    label, r_path, seat, post_quota = args
    import submission_rc4_1_clean as rc41_mod
    rc41_mod._POST_CONFIRM_SAFE_QUOTA = post_quota
    
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
    
    straw_rev_pre = 0.0
    straw_rev_post = 0.0
    other_rev = 0.0
    confirm_day = None
    confirm_hour = None
    
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
                    if item == "STRAWBERRY":
                        if confirm_day is None or day <= confirm_day:
                            straw_rev_pre += r
                        else:
                            straw_rev_post += r
                    else:
                        other_rev += r
                        
        env.step(acts)
        
    score = env.state[seat].observation.farms[seat].money
    return {
        "label": label,
        "seat": seat,
        "quota": post_quota,
        "score": score,
        "confirm_day": confirm_day,
        "confirm_hour": confirm_hour,
        "straw_pre": straw_rev_pre,
        "straw_post": straw_rev_post,
        "other_rev": other_rev
    }

if __name__ == "__main__":
    sweep_tasks = []
    for label, r_path, seat in targets:
        for q in (12, 10, 8, 6):
            sweep_tasks.append((label, r_path, seat, q))
            
    print("=" * 135)
    print("PHASE 15: VECTOR 2 POST-CONFIRMATION QUOTA SWEEP (NATIVE RC4.1 ENGINE: QUOTA 12 vs 10 vs 8 vs 6)")
    print("=" * 135)
    print(f"{'REGIME':<30} | {'QUOTA':>5} | {'SCORE':>10} | {'DIFF(vs 10)':>11} | {'CONFIRM':>8} | {'PRE-STRAW':>11} | {'POST-STRAW':>11} | {'OTHER REV':>11}")
    print("-" * 135)
    sys.stdout.flush()
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_quota_sim, sweep_tasks))
        
    # Group by regime
    by_regime = {}
    for r in results:
        by_regime.setdefault(r["label"], {})[r["quota"]] = r
        
    for label, q_dict in by_regime.items():
        base_10_score = q_dict[10]["score"]
        for q in (12, 10, 8, 6):
            r = q_dict[q]
            diff = r["score"] - base_10_score
            c_str = f"D{r['confirm_day']} H{r['confirm_hour']}" if r["confirm_day"] else "NO"
            print(f"{label:<30} | {q:>5} | ${r['score']:>9,.0f} | ${diff:>+10,.0f} | {c_str:>8} | ${r['straw_pre']:>10,.0f} | ${r['straw_post']:>10,.0f} | ${r['other_rev']:>10,.0f}")
        print("-" * 135)
        sys.stdout.flush()
        
    print("=" * 135)
