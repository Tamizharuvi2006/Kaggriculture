import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

# We will simulate synthetic opponent strawberry exposures on Day 11 across: 12, 16, 18, 20, 22, 25, 30
exposures = [12, 16, 18, 20, 22, 25, 30]

seed = 628719714 # Use clean baseline seed

def run_exposure_sim(opp_count, use_h6=True):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    orig_crop_plan = rc2_mod._crop_plan
    
    straw_rev = 0.0
    other_rev = 0.0
    peak_inv = 0
    days_over_10k = set()
    min_p = 999.0
    our_straw_bushes = 0
    
    for step in range(720):
        if env.done: break
        obs1 = env.state[1].observation
        day = obs1.day
        hour = obs1.hour
        
        mkt = obs1.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        p_straw = float(mkt.prices.get("STRAWBERRY", 120))
        
        if inv_straw > peak_inv: peak_inv = inv_straw
        if inv_straw > 10000: days_over_10k.add(day)
        if p_straw < min_p: min_p = p_straw
        
        # Apply H6 logic
        if use_h6 and day >= 11 and opp_count >= 16:
            safe_quota = max(10, 26 - opp_count)
            def patched_crop_plan(d):
                p = orig_crop_plan(d)
                s_count = 0
                new_p = {}
                for pos, c in p.items():
                    if c == "STRAWBERRY":
                        if s_count < safe_quota:
                            new_p[pos] = "STRAWBERRY"
                            s_count += 1
                        else:
                            new_p[pos] = "CARROT"
                    else:
                        new_p[pos] = c
                return new_p
            rc2_mod._crop_plan = patched_crop_plan
        else:
            rc2_mod._crop_plan = orig_crop_plan
            
        try:
            act0 = rc2_mod.agent(env.state[0].observation)
            act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        # If testing synthetic opponent exposure: inject opponent strawberry sales to match opp_count
        # Each bush produces 1 strawberry every 2 days
        if day >= 11 and step % 48 == 0 and opp_count > 0:
            # Opponent sells opp_count strawberries every 2 days
            if isinstance(act0, dict):
                m = act0.get("market", [])
                m.append(["SELL", "STRAWBERRY", opp_count])
                act0["market"] = m
                
        # Track our revenue
        if isinstance(act1, dict):
            for ord_item in act1.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY": straw_rev += r
                    else: other_rev += r
                    
        # Count our bushes on Day 15
        if day == 15 and hour == 0:
            f1 = obs1.farms[1]
            our_straw_bushes = sum(1 for row in f1.tiles for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            
        env.step([act0, act1])
        
    final_score = env.state[1].observation.farms[1].money
    return {
        "score": final_score,
        "our_bushes": our_straw_bushes,
        "peak_inv": peak_inv,
        "days_over_10k": len(days_over_10k),
        "min_p": min_p,
        "straw_rev": straw_rev,
        "other_rev": other_rev
    }

print("=" * 115)
print("BOUNDARY EXPOSURE MECHANISM VALIDATION: RC2 vs H6 (Threshold >= 16)")
print("=" * 115)
print(f"{'OPP STRAW':<10} | {'MODE':<6} | {'OUR BUSH':>8} | {'PEAK INV':>9} | {'DAYS>10k':>8} | {'MIN PRICE':>9} | {'STRAW REV':>11} | {'OTHER REV':>11} | {'FINAL SCORE':>12}")
print("-" * 115)

for exp in exposures:
    # Run RC2
    r_rc2 = run_exposure_sim(exp, use_h6=False)
    # Run H6
    r_h6 = run_exposure_sim(exp, use_h6=True)
    
    print(f"{exp:<10} | {'RC2':<6} | {r_rc2['our_bushes']:>8} | {r_rc2['peak_inv']:>9,} | {r_rc2['days_over_10k']:>8} | ${r_rc2['min_p']:>8.1f} | ${r_rc2['straw_rev']:>10,.0f} | ${r_rc2['other_rev']:>10,.0f} | ${r_rc2['score']:>11,.0f}")
    print(f"{'':<10} | {'H6':<6} | {r_h6['our_bushes']:>8} | {r_h6['peak_inv']:>9,} | {r_h6['days_over_10k']:>8} | ${r_h6['min_p']:>8.1f} | ${r_h6['straw_rev']:>10,.0f} | ${r_h6['other_rev']:>10,.0f} | ${r_h6['score']:>11,.0f} (Diff: ${r_h6['score']-r_rc2['score']:>+7,.0f})")
    print("-" * 115)

print("=" * 115)
