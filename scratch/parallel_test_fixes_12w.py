import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_simulation(args):
    ep_file, fix_melon_clearance, fix_late_feed, fix_min_cash_buffer = args
    import kaggle_environments
    import submission_challenger_exp208_clean as challenger
    
    with open(ep_file, "r", encoding="utf-8") as f:
        replay = json.load(f)
        
    eid = replay.get("info", {}).get("EpisodeId")
    seed = replay.get("info", {}).get("seed")
    rewards = replay.get("rewards", [])
    agents = replay.get("info", {}).get("Agents", [])
    
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    orig_h = rewards[hero_idx]
    orig_o = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    opp_actions = [frame[opp_idx].get("action") for frame in steps[1:]]
    
    # Define custom agent wrapper with the tested fixes
    def tested_agent(obs):
        act = challenger.agent(obs)
        if not isinstance(act, dict): return act
        
        step = obs.get("step") if isinstance(obs, dict) else getattr(obs, "step", None)
        if step is None:
            step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
        day = step // 24
        hour = step % 24
        
        farms = obs.get("farms", [{}, {}])
        own = farms[hero_idx] if len(farms) > hero_idx else {}
        money = float(own.get("money", 0))
        priv = obs.get("private", {})
        shed = priv.get("shed", {})
        
        mkt = list(act.get("market", []))
        
        # Fix 1: Full end of game liquidation (including MELON and WHEAT)
        if fix_melon_clearance and step >= 690:
            clean = []
            for prod in ("STRAWBERRY", "MELON", "MILK", "FERTILIZER", "WOOL", "WHEAT"):
                qty = int(shed.get(prod, 0) or 0)
                if qty > 0:
                    clean.append(["SELL", prod, qty])
            if clean:
                act["market"] = clean
                return act
                
        # Fix 2: Late Feed Purchase Cap (don't buy wheat feed on Day 28+ as it won't repay)
        if fix_late_feed and day >= 28:
            mkt = [m for m in mkt if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]
            
        # Fix 3: Emergency Cash Liquidity Buffer (sell fertilizer if money < $120 to prevent starvation)
        if fix_min_cash_buffer and money < 120.0:
            fert_qty = int(shed.get("FERTILIZER", 0) or 0)
            if fert_qty >= 1 and not any(isinstance(m, list) and len(m) >= 2 and m[0] == "SELL" and m[1] == "FERTILIZER" for m in mkt):
                mkt.insert(0, ["SELL", "FERTILIZER", fert_qty])
                
        act["market"] = mkt
        return act

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    challenger._V18_SELECTED_DAY = {0: None, 1: None}
    challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs_hero = env.state[hero_idx].observation
        act_hero = tested_agent(obs_hero)
        act_opp = opp_actions[s]
        
        actions = [None, None]
        actions[hero_idx] = act_hero
        actions[opp_idx] = act_opp
        env.step(actions)
        
    fin_h = env.state[hero_idx].reward
    fin_o = env.state[opp_idx].reward
    
    return eid, fix_melon_clearance, fix_late_feed, fix_min_cash_buffer, orig_h, orig_o, fin_h, fin_o

def main():
    import glob
    ep_files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")
    print(f"Loaded {len(ep_files)} live loss replay files.")
    
    # Configurations to test
    configs = [
        # (melon_clearance, late_feed_cap, min_cash_buffer)
        (False, False, False), # Baseline
        (True, False, False),  # Only Melon + Wheat clearance
        (False, True, False),  # Only Late Feed Cap
        (False, False, True),  # Only Emergency Liquidity
        (True, True, False),   # Clearance + Late Feed Cap
        (True, True, True),    # All Three Combined
    ]
    
    tasks = []
    for ep in ep_files:
        for c in configs:
            tasks.append((ep, c[0], c[1], c[2]))
            
    print(f"Evaluating {len(tasks)} scenarios across 12 parallel workers...")
    t0 = time.time()
    
    results_by_config = {}
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_simulation, task): task for task in tasks}
        for fut in as_completed(futures):
            eid, f_m, f_f, f_b, orig_h, orig_o, fin_h, fin_o = fut.result()
            cfg = (f_m, f_f, f_b)
            if cfg not in results_by_config:
                results_by_config[cfg] = []
            results_by_config[cfg].append({
                "eid": eid,
                "orig_h": orig_h,
                "orig_o": orig_o,
                "fin_h": fin_h,
                "fin_o": fin_o,
                "gain": fin_h - orig_h,
                "margin": fin_h - fin_o
            })
            
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f}s\n")
    
    print("=" * 115)
    print(f"{'Config (Clearance, LateFeed, CashBuffer)':>42} | {'Original Mean ($)':>18} | {'Counterfactual ($)':>18} | {'Net Gain ($)':>15} | {'Win Count':>10}")
    print("=" * 115)
    
    for cfg in configs:
        matches = results_by_config[cfg]
        mean_orig = sum(m["orig_h"] for m in matches) / len(matches)
        mean_fin = sum(m["fin_h"] for m in matches) / len(matches)
        net_gain = mean_fin - mean_orig
        wins = sum(1 for m in matches if m["fin_h"] > m["fin_o"])
        cfg_str = f"Clearance={str(cfg[0])[0]}, LateFeed={str(cfg[1])[0]}, Buffer={str(cfg[2])[0]}"
        print(f"{cfg_str:>42} | ${mean_orig:16,.0f} | ${mean_fin:16,.0f} | ${net_gain:+13,.0f} | {wins:2d}/{len(matches)} W")
        
    print("\nDetailed Per-Episode Breakdown for Best Configuration:")
    best_cfg = (True, True, True)
    for m in sorted(results_by_config[best_cfg], key=lambda x: x["eid"]):
        print(f"  Episode {m['eid']}: Orig ${m['orig_h']:,.0f} (vs Opp ${m['orig_o']:,.0f}) -> New ${m['fin_h']:,.0f} (Gain: {m['gain']:+,.0f}, Margin: {m['margin']:+,.0f})")

if __name__ == "__main__":
    main()
