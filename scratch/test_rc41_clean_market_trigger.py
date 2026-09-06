import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"

def run_rc41_clean(threshold=9935, replay_path=None, seed_val=None, seat=1):
    if replay_path:
        with open(replay_path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = seed_val
        opp_actions = None
        max_steps = 720
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    potential_risk = False
    flood_confirmed = False
    confirm_day = None
    confirm_hour = None
    
    prev_inv = 10000
    straw_rev = 0.0
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
        
        # Stage 1: Day 11 Hour 0 Forecast (Opponent Capacity)
        if day == 11 and hour == 0:
            opp_farm = obs.farms[1 - seat]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True
                
        # Stage 3: Realized Market Inventory Response (Strictly Market State!)
        # Day 15+: If market inventory crosses calibrated threshold with positive velocity (ΔI > 0)
        if potential_risk and day >= 15 and not flood_confirmed:
            if inv_straw >= threshold and delta_inv > 0:
                flood_confirmed = True
                confirm_day = day
                confirm_hour = hour
                
        # Adaptive Allocation:
        # Pre-confirmation: allow 24 bushes (Policy C: 2 flexible buffer plots)
        # Post-confirmation: restrict to 10 bushes and divert remainder to Carrots/Feed!
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
            if replay_path:
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
                    if item == "STRAWBERRY": straw_rev += r
                    else: other_rev += r
                    
        env.step(acts)
        
    return {
        "score": env.state[seat].observation.farms[seat].money,
        "confirm_day": confirm_day,
        "confirm_hour": confirm_hour,
        "straw_rev": straw_rev,
        "other_rev": other_rev
    }

print("=" * 115)
print("RC4.1-CLEAN EVALUATION: STAGE 3 REALIZED MARKET RESPONSE (THRESHOLD = 9,935)")
print("=" * 115)
print(f"{'TARGET REGIME':<28} | {'SCORE':>12} | {'CONFIRMED?':>11} | {'CONFIRM TIME':>14} | {'STRAW REV':>12} | {'OTHER REV':>12}")
print("-" * 115)

targets = [
    ("Soumi Ghosh (Active Flooder)", path_soumi, None),
    ("arao (Passive Holder)", path_arao, None),
    ("Seed 628719714 (High Ceiling)", None, 628719714),
]

for label, r_path, s_val in targets:
    res = run_rc41_clean(threshold=9935, replay_path=r_path, seed_val=s_val)
    conf_str = "YES" if res["confirm_day"] is not None else "NO"
    time_str = f"D{res['confirm_day']} H{res['confirm_hour']}" if res["confirm_day"] is not None else "-"
    print(f"{label:<28} | ${res['score']:>11,.0f} | {conf_str:>11} | {time_str:>14} | ${res['straw_rev']:>11,.0f} | ${res['other_rev']:>11,.0f}")

print("=" * 115)
