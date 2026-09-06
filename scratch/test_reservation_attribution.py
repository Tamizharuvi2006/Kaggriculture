import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"

def run_res_sim(reserve_plots, replay_path=None, seed_val=None):
    if replay_path:
        with open(replay_path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[0].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = seed_val
        opp_actions = None
        max_steps = 720
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    potential_risk = False
    flood_confirmed = False
    prev_inv = 10000
    straw_rev = 0.0
    other_rev = 0.0
    
    orig_crop_plan = rc2_mod._crop_plan
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[1].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        delta_inv = inv_straw - prev_inv
        prev_inv = inv_straw
        
        if day == 11 and hour == 0:
            opp_farm = obs.farms[0]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True
                
        if potential_risk and day >= 12 and not flood_confirmed:
            if inv_straw >= 9960 and delta_inv > 0:
                flood_confirmed = True
                
        # Reservation sizing:
        # Pre-confirmation quota: 26 - reserve_plots (e.g. 0 -> 26, 1 -> 25, 2 -> 24)
        # Post-confirmation quota: 10
        if potential_risk and day >= 11:
            quota = 10 if flood_confirmed else (26 - reserve_plots)
            rc2_mod._crop_plan = lambda d: {
                pos: ("CARROT" if c == "STRAWBERRY" and i >= quota else c)
                for i, (pos, c) in enumerate(orig_crop_plan(d).items())
            }
        else:
            rc2_mod._crop_plan = orig_crop_plan
            
        try:
            if replay_path:
                act0 = opp_actions[step]
                act1 = rc2_mod.agent(env.state[1].observation)
            else:
                act0 = rc2_mod.agent(env.state[0].observation)
                act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        if isinstance(act1, dict):
            for ord_item in act1.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY": straw_rev += r
                    else: other_rev += r
                    
        env.step([act0, act1])
        
    return env.state[1].observation.farms[1].money, flood_confirmed, straw_rev, other_rev

print("=" * 95)
print("RESERVATION ATTRIBUTION TEST: 0 vs 1 vs 2 PLOTS (ARAO, SOUMI, HIGH CEILING)")
print("=" * 95)
print(f"{'TARGET':<25} | {'RESERVE (PLOTS)':<16} | {'SCORE':>10} | {'CONFIRMED?':>11} | {'STRAW REV':>11} | {'OTHER REV':>11}")
print("-" * 95)

targets = [
    ("Arao (Passive)", path_arao, None),
    ("Soumi (Flooder)", path_soumi, None),
    ("Seed 628719714 (Ceiling)", None, 628719714)
]

for t_name, r_path, s_val in targets:
    for res_plots in [0, 1, 2]:
        score, conf, s_rev, o_rev = run_res_sim(res_plots, r_path, s_val)
        conf_str = "YES" if conf else "NO"
        print(f"{t_name:<25} | {res_plots} Plot(s) Reserve | ${score:>9,.0f} | {conf_str:>11} | ${s_rev:>10,.0f} | ${o_rev:>10,.0f}")
    print("-" * 95)

print("=" * 95)
