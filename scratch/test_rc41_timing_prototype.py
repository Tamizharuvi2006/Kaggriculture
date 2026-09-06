import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"

def run_agent_variant(variant, replay_path=None, seed_val=None, seat=1):
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
    
    prev_inv = 10000
    opp_sales_history = []
    
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
        
        # Day 11 Hour 0: Forecast potential risk
        if day == 11 and hour == 0:
            opp_farm = obs.farms[1 - seat]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True
                
        # Track opponent strawberry sales in step
        if replay_path:
            opp_act = opp_actions[step]
        else:
            opp_act = rc2_mod.agent(env.state[1 - seat].observation)
            
        opp_straw_sold_step = 0
        if isinstance(opp_act, dict):
            for o in opp_act.get("market", []):
                if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                    # Cap by actual shed units if macro order
                    opp_straw_sold_step += min(o[2], 100) # realistic batch
        opp_sales_history.append(opp_straw_sold_step)
        opp_sales_24h = sum(opp_sales_history[-24:])
        
        # Confirmation Logic by Variant
        if variant == "RC2":
            rc2_mod._crop_plan = orig_crop_plan
        elif variant == "RC3":
            # RC3 cuts immediately at Day 11 if risk flagged
            if potential_risk and day >= 11:
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= 10 else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
        elif variant == "RC4":
            # RC4: Late confirmation (Day 21-23 threshold: inv >= 9960 and delta_inv > 0)
            if potential_risk and day >= 12 and not flood_confirmed:
                if inv_straw >= 9960 and delta_inv > 0:
                    flood_confirmed = True
                    confirm_day = day
            if potential_risk and day >= 11:
                quota = 10 if flood_confirmed else 24
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
        elif variant == "RC4.1":
            # RC4.1: Day 15-18 Physical Window Confirmation
            # Triggers if: (day >= 15 and opp_sales_24h >= 15) OR (day >= 15 and inv_straw >= 9940 and delta_inv > 0)
            if potential_risk and day >= 15 and not flood_confirmed:
                if opp_sales_24h >= 15 or (inv_straw >= 9940 and delta_inv > 0):
                    flood_confirmed = True
                    confirm_day = day
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
        "straw_rev": straw_rev,
        "other_rev": other_rev
    }

print("=" * 115)
print("FOUR-WAY TIMING WINDOW EXPERIMENT: RC2 vs RC3 vs RC4 vs RC4.1 (DAY 15-18 WINDOW)")
print("=" * 115)
print(f"{'TARGET REGIME':<26} | {'RC2 CONTROL':>12} | {'RC3 BASELINE':>12} | {'RC4 (LATE D23)':>14} | {'RC4.1 (DAY 16)':>14} | {'CONFIRM DAY':>12}")
print("-" * 115)

targets = [
    ("Soumi Ghosh (Active Flooder)", path_soumi, None),
    ("arao (Passive Holder)", path_arao, None),
    ("Seed 628719714 (High Ceiling)", None, 628719714),
]

for label, r_path, s_val in targets:
    r2 = run_agent_variant("RC2", r_path, s_val)
    r3 = run_agent_variant("RC3", r_path, s_val)
    r4 = run_agent_variant("RC4", r_path, s_val)
    r41 = run_agent_variant("RC4.1", r_path, s_val)
    
    c_day_str = f"D{r41['confirm_day']}" if r41['confirm_day'] else "NO"
    print(f"{label:<26} | ${r2['score']:>11,.0f} | ${r3['score']:>11,.0f} | ${r4['score']:>13,.0f} | ${r41['score']:>13,.0f} | {c_day_str:>12}")

print("=" * 115)
