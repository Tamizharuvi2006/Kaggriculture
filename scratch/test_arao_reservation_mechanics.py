import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"

def run_policy_sim(policy_name, replay_path, label):
    with open(replay_path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[0].get("action") for frame in steps[1:]]
    max_steps = len(steps) - 1
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    potential_risk = False
    flood_confirmed = False
    first_warning_day = None
    confirmation_day = None
    
    prev_inv = 10000
    straw_rev = 0.0
    other_rev = 0.0
    diverted_plots = 0
    
    orig_crop_plan = rc2_mod._crop_plan
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[1].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        p_straw = float(mkt.prices.get("STRAWBERRY", 120))
        delta_inv = inv_straw - prev_inv
        prev_inv = inv_straw
        
        # Day 11 Hour 0: Observe opponent strawberry exposure
        if day == 11 and hour == 0:
            opp_farm = obs.farms[0]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True
                first_warning_day = day
                
        # Day 12+: Check for confirmed flood (inv >= 9960 and delta_inv > 0)
        if potential_risk and day >= 12 and not flood_confirmed:
            if inv_straw >= 9960 and delta_inv > 0:
                flood_confirmed = True
                confirmation_day = day
                
        # Apply Crop Plan Policies
        if policy_name == "RC2_CONTROL":
            rc2_mod._crop_plan = orig_crop_plan
        elif policy_name == "POLICY_A_CURRENT":
            # Policy A: restrict to 22 pre-confirmation, 10 post-confirmation
            if potential_risk and day >= 11:
                quota = 10 if flood_confirmed else 22
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
        elif policy_name == "POLICY_B_ZERO_RESERVATION":
            # Policy B: 100% full 26-strawberry allocation pre-confirmation!
            # ONLY if flood is confirmed do we cut future allocation to 10!
            if potential_risk and day >= 11:
                quota = 10 if flood_confirmed else 26
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
        elif policy_name == "POLICY_C_MINIMAL_RESERVATION":
            # Policy C: 24 pre-confirmation (2 flexible plots held), 10 post-confirmation
            if potential_risk and day >= 11:
                quota = 10 if flood_confirmed else 24
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
                
        try:
            act0 = opp_actions[step]
            act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        # Track sales
        if isinstance(act1, dict):
            for ord_item in act1.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY": straw_rev += r
                    else: other_rev += r
                    
        env.step([act0, act1])
        
    final_score = env.state[1].observation.farms[1].money
    f1 = env.state[1].observation.farms[1]
    final_straw_bushes = sum(1 for r in f1.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
    
    return {
        "label": label,
        "policy": policy_name,
        "score": final_score,
        "confirmed": flood_confirmed,
        "warning_day": first_warning_day,
        "confirm_day": confirmation_day,
        "straw_bushes": final_straw_bushes,
        "straw_rev": straw_rev,
        "other_rev": other_rev
    }

print("=" * 115)
print("CONTROLLED MECHANISM EXPERIMENT: OPTIONALITY & RESERVATION POLICIES ON ARAO & SOUMI")
print("=" * 115)
print(f"{'TARGET':<15} | {'POLICY':<26} | {'SCORE':>10} | {'CONFIRMED?':>11} | {'DAY':>5} | {'BUSHES':>7} | {'STRAW REV':>11} | {'OTHER REV':>11}")
print("-" * 115)

policies = [
    "RC2_CONTROL",
    "POLICY_A_CURRENT",
    "POLICY_B_ZERO_RESERVATION",
    "POLICY_C_MINIMAL_RESERVATION"
]

for p_path, target_lbl in [(path_arao, "Arao (Passive)"), (path_soumi, "Soumi (Flooder)")]:
    for pol in policies:
        res = run_policy_sim(pol, p_path, target_lbl)
        conf_str = "YES" if res["confirmed"] else "NO"
        c_day_str = f"D{res['confirm_day']}" if res["confirm_day"] is not None else "-"
        print(f"{target_lbl:<15} | {pol:<26} | ${res['score']:>9,.0f} | {conf_str:>11} | {c_day_str:>5} | {res['straw_bushes']:>7} | ${res['straw_rev']:>10,.0f} | ${res['other_rev']:>10,.0f}")
    print("-" * 115)

print("=" * 115)
