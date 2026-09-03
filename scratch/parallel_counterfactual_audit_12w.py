import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def evaluate_case(args):
    ep_file, wf, mf, sf = args
    import kaggle_environments
    
    with open(ep_file, "r", encoding="utf-8") as f:
        replay = json.load(f)
        
    info = replay.get("info", {})
    eid = info.get("EpisodeId")
    seed = info.get("seed")
    rewards = replay.get("rewards", [])
    agents = info.get("Agents", [])
    
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    
    orig_hero_rew = rewards[hero_idx]
    orig_opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    if len(steps) < 100:
        return eid, wf, mf, sf, 0, 0, 0, 0
        
    opp_actions = [frame[opp_idx].get("action") for frame in steps[1:]]
    hero_actions = [frame[hero_idx].get("action") for frame in steps[1:]]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    for s in range(len(opp_actions)):
        if env.done:
            break
            
        act_opp = opp_actions[s]
        act_hero = json.loads(json.dumps(hero_actions[s])) if hero_actions[s] else {"farmer": ["PASS"], "hands": [], "market": []}
        
        obs_hero = env.state[hero_idx].observation
        prices = obs_hero.get("market", {}).get("prices", {})
        p_wool = float(prices.get("WOOL", 200))
        p_milk = float(prices.get("MILK", 160))
        p_straw = float(prices.get("STRAWBERRY", 120))
        
        # Anti-fire-sale filter for midgame (s < 690)
        if s < 690 and "market" in act_hero:
            clean_mkt = []
            for order in act_hero.get("market", []):
                if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL":
                    prod = order[1]
                    if prod == "WOOL" and p_wool < wf:
                        continue
                    if prod == "MILK" and p_milk < mf:
                        continue
                    if prod == "STRAWBERRY" and p_straw < sf:
                        continue
                clean_mkt.append(order)
            act_hero["market"] = clean_mkt
        elif s >= 690:
            # Complete clearance of everything in shed at step 690+
            priv = obs_hero.get("private", {})
            shed = priv.get("shed", {})
            clean_orders = []
            for prod in ("STRAWBERRY", "MELON", "MILK", "FERTILIZER", "WOOL", "WHEAT"):
                qty = int(shed.get(prod, 0) or 0)
                if qty > 0:
                    clean_orders.append(["SELL", prod, qty])
            if clean_orders:
                act_hero["market"] = clean_orders
                
        actions = [None, None]
        actions[hero_idx] = act_hero
        actions[opp_idx] = act_opp
        env.step(actions)
        
    final_hero = env.state[hero_idx].reward
    final_opp = env.state[opp_idx].reward
    
    return eid, wf, mf, sf, orig_hero_rew, orig_opp_rew, final_hero, final_opp

def main():
    print("=========================================================================================")
    print("     PARALLEL 12-WORKER COUNTERFACTUAL AUDIT ON ACTUAL LIVE LOSS REPLAYS                 ")
    print("=========================================================================================")
    
    import glob
    ep_files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")
    print(f"Loaded {len(ep_files)} live match replays.")
    
    # Grid of floor settings to evaluate across all live loss replays
    tasks = []
    # Test baseline (1, 1, 1) and protected floors
    configs = [
        (1, 1, 1),
        (30, 20, 20),
        (50, 30, 30),
        (70, 40, 40),
        (90, 50, 50),
    ]
    for ep in ep_files:
        for wf, mf, sf in configs:
            tasks.append((ep, wf, mf, sf))
            
    print(f"Evaluating {len(tasks)} simulation scenarios across 12 parallel workers...")
    t0 = time.time()
    
    results_by_config = {}
    
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(evaluate_case, task): task for task in tasks}
        for fut in as_completed(futures):
            eid, wf, mf, sf, orig_h, orig_o, fin_h, fin_o = fut.result()
            cfg = (wf, mf, sf)
            if cfg not in results_by_config:
                results_by_config[cfg] = []
            results_by_config[cfg].append({
                "eid": eid,
                "orig_h": orig_h,
                "orig_o": orig_o,
                "fin_h": fin_h,
                "fin_o": fin_o,
                "delta": fin_h - fin_o,
                "gain": fin_h - orig_h
            })
            
    elapsed = time.time() - t0
    print(f"\nExecution completed in {elapsed:.2f}s ({len(tasks)/elapsed:.1f} matches/sec)\n")
    
    print("=" * 115)
    print(f"{'Configuration (W, M, S)':>25} | {'Original Mean ($)':>18} | {'Counterfactual ($)':>18} | {'Net Gain ($)':>15} | {'Win Count':>10}")
    print("=" * 115)
    
    for cfg in configs:
        matches = results_by_config[cfg]
        mean_orig = sum(m["orig_h"] for m in matches) / len(matches)
        mean_fin = sum(m["fin_h"] for m in matches) / len(matches)
        net_gain = mean_fin - mean_orig
        wins = sum(1 for m in matches if m["fin_h"] > m["fin_o"])
        print(f"Floors (W>{cfg[0]:2d}, M>{cfg[1]:2d}, S>{cfg[2]:2d}) | ${mean_orig:16,.0f} | ${mean_fin:16,.0f} | ${net_gain:+13,.0f} | {wins:2d}/{len(matches)} W")

    # Detailed report on the best configuration vs each episode
    best_cfg = (70, 40, 40)
    if best_cfg in results_by_config:
        print(f"\nBreakdown for Best Configuration (Wool>70, Milk>40, Straw>40):")
        for m in results_by_config[best_cfg]:
            print(f"  Ep {m['eid']}: Orig ${m['orig_h']:,.0f} (vs Opp ${m['orig_o']:,.0f}) -> New ${m['fin_h']:,.0f} (Gain: {m['gain']:+,.0f}, Result: {'WIN' if m['fin_h'] > m['fin_o'] else 'LOSS'})")

if __name__ == "__main__":
    main()
