import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(replay_path) as f:
    rep = json.load(f)

seed = rep["info"]["seed"]
steps = rep["steps"]
seat = 1 # We are Seat 1
opp_actions = [frame[0].get("action") for frame in steps[1:]]

def run_audit(divert_on_saturation=False):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    saturation_day = None
    post_sat_straw_seeds = 0
    post_sat_straw_harvests = 0
    post_sat_straw_revenue = 0
    
    for step in range(len(steps) - 1):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        p_straw = float(mkt.prices.get("STRAWBERRY", 120))
        
        is_saturated = (inv_straw >= 10000)
        if is_saturated and saturation_day is None:
            saturation_day = day
            
        act0 = opp_actions[step]
        
        # Patch crop plan if counterfactual
        orig_crop_plan = rc2_mod._crop_plan
        if divert_on_saturation and is_saturated:
            def patched_crop_plan(d):
                p = orig_crop_plan(d)
                # Divert any new STRAWBERRY plots to WHEAT or CARROT
                return {pos: ("WHEAT" if c == "STRAWBERRY" else c) for pos, c in p.items()}
            rc2_mod._crop_plan = patched_crop_plan
            
        try:
            act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        # Track sales
        if is_saturated:
            mkt_orders = act1.get("market", []) if isinstance(act1, dict) else []
            for ord_item in mkt_orders:
                if len(ord_item) >= 3 and ord_item[0] == "BUY_SEED" and ord_item[1] == "STRAWBERRY":
                    post_sat_straw_seeds += ord_item[2]
                elif len(ord_item) >= 3 and ord_item[0] == "SELL" and ord_item[1] == "STRAWBERRY":
                    post_sat_straw_harvests += ord_item[2]
                    post_sat_straw_revenue += ord_item[2] * p_straw * 0.95
                    
        env.step([act0, act1])
        
    final_score = env.state[seat].observation.farms[seat].money
    priv = env.state[seat].observation.private
    shed = priv.get("shed", {})
    return {
        "final_score": final_score,
        "saturation_day": saturation_day,
        "post_sat_seeds": post_sat_straw_seeds,
        "post_sat_harvests": post_sat_straw_harvests,
        "post_sat_revenue": post_sat_straw_revenue,
        "final_shed": sum(shed.values())
    }

print("=" * 105)
print("COUNTERFACTUAL AUDIT: STRAWBERRY SATURATION AVOIDANCE (SOUMI GHOSH SEAT 1)")
print("=" * 105)

print("\n1. Running Baseline RC2...")
r_base = run_audit(divert_on_saturation=False)

print("\n2. Running Counterfactual (Divert Strawberry to Wheat when Inv >= 10,000)...")
r_cf = run_audit(divert_on_saturation=True)

print("\n" + "=" * 105)
print(f"{'METRIC':<45} | {'BASELINE RC2':>20} | {'COUNTERFACTUAL (DIVERT)':>25}")
print("-" * 105)
print(f"{'Final Score':<45} | ${r_base['final_score']:>19,.0f} | ${r_cf['final_score']:>24,.0f}")
print(f"{'First Saturation Day':<45} | Day {r_base['saturation_day']:>15} | Day {r_cf['saturation_day']:>20}")
print(f"{'Post-Saturation Strawberry Seeds Bought':<45} | {r_base['post_sat_seeds']:>20} | {r_cf['post_sat_seeds']:>25}")
print(f"{'Post-Saturation Strawberries Sold':<45} | {r_base['post_sat_harvests']:>20} | {r_cf['post_sat_harvests']:>25}")
print(f"{'Post-Saturation Strawberry Revenue Realized':<45} | ${r_base['post_sat_revenue']:>19,.0f} | ${r_cf['post_sat_revenue']:>24,.0f}")
print(f"{'Final Score Delta':<45} | {'-':>20} | ${r_cf['final_score'] - r_base['final_score']:>+24,.0f}")
print("=" * 105)

# Also test on the High Ceiling run (Seed 628719714) to confirm ZERO CEILING DAMAGE!
print("\n3. Testing Counterfactual on High-Ceiling Seed 628719714 (Control vs Counterfactual)...")
env_h_base = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 628719714})
env_h_base.reset()
for s in range(720):
    if env_h_base.done: break
    act0 = rc2_mod.agent(env_h_base.state[0].observation)
    act1 = rc2_mod.agent(env_h_base.state[1].observation)
    env_h_base.step([act0, act1])
score_h_base = env_h_base.state[1].observation.farms[1].money

# Now run with patched crop plan on Seed 628719714
env_h_cf = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 628719714})
env_h_cf.reset()
for s in range(720):
    if env_h_cf.done: break
    obs0 = env_h_cf.state[0].observation
    obs1 = env_h_cf.state[1].observation
    is_sat = (int(obs1.market.inventory.get("STRAWBERRY", 10000)) >= 10000)
    orig_p = rc2_mod._crop_plan
    if is_sat:
        rc2_mod._crop_plan = lambda d: {pos: ("WHEAT" if c == "STRAWBERRY" else c) for pos, c in orig_p(d).items()}
    try:
        act0 = rc2_mod.agent(obs0)
        act1 = rc2_mod.agent(obs1)
    finally:
        rc2_mod._crop_plan = orig_p
    env_h_cf.step([act0, act1])
score_h_cf = env_h_cf.state[1].observation.farms[1].money

print(f"High Ceiling Score (Baseline RC2):        ${score_h_base:,.0f}")
print(f"High Ceiling Score (Counterfactual):       ${score_h_cf:,.0f}")
print(f"Ceiling Delta:                             ${score_h_cf - score_h_base:+,.0f}")
print("=" * 105)
