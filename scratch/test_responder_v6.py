import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_sim(args):
    replay_file, target_player_idx, policy_mode = args
    import kaggle_environments
    import submission_challenger_exp208_clean as base_challenger
    
    with open(replay_file, "r", encoding="utf-8") as f:
        replay = json.load(f)
        
    info = replay.get("info", {})
    seed = info.get("seed")
    agents = info.get("Agents", [])
    rewards = replay.get("rewards", [])
    
    cand_idx = target_player_idx
    opp_idx = 1 - cand_idx
    
    opp_name = agents[opp_idx].get("Name", f"Player {opp_idx}")
    orig_cand_rew = rewards[cand_idx]
    orig_opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    opp_actions = [frame[opp_idx].get("action") for frame in steps[1:]]
    
    def policy_agent(obs):
        step = obs.get("step") if isinstance(obs, dict) else getattr(obs, "step", None)
        if step is None:
            step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
        day = step // 24
        hour = step % 24
        
        farms = obs.get("farms", [{}, {}])
        own = farms[cand_idx] if len(farms) > cand_idx else {}
        opp = farms[opp_idx] if len(farms) > opp_idx else {}
        
        act = base_challenger.agent(obs)
        if not isinstance(act, dict): return act
        
        if policy_mode == "baseline":
            return act
            
        mkt = list(act.get("market") or [])
        money = float(own.get("money", 0) or 0)
        own_quads = len(own.get("unlocked_quadrants", []) or [])
        opp_quads = len(opp.get("unlocked_quadrants", []) or [])
        
        mkt_info = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt_info.get("prices") or {}
        p_wool = float(prices.get("WOOL", 180.0) or 180.0)
        p_milk = float(prices.get("MILK", 80.0) or 80.0)
        p_wheat = float(prices.get("WHEAT", 30.0) or 30.0)
        
        opp_cows, opp_sheep = 0, 0
        for r in (opp.get("tiles") or []):
            for t in r:
                if isinstance(t, dict):
                    if t.get("animal") == "COW": opp_cows += 1
                    elif t.get("animal") == "SHEEP": opp_sheep += 1
        opp_animals = opp_cows + opp_sheep
        
        own_cows, own_sheep = 0, 0
        for r in (own.get("tiles") or []):
            for t in r:
                if isinstance(t, dict):
                    if t.get("animal") == "COW": own_cows += 1
                    elif t.get("animal") == "SHEEP": own_sheep += 1
        own_animals = own_cows + own_sheep
        
        if policy_mode == "responder_v5":
            if own_quads == 1 and 6 <= day <= 7 and opp_quads >= 2 and money >= 930.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            if own_quads == 2 and 8 <= day <= 11 and opp_quads >= 3 and money >= 1150.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            if own_quads >= 2 and 8 <= day <= 15 and opp_animals >= 4:
                if own_cows < 8 and money >= 850.0 and own_animals < opp_animals + 1:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                        mkt.append(["BUY_ANIMAL", "COW"])
            if day >= 22 and (p_wool < 45.0 or day >= 25):
                mkt = [m for m in mkt if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

        elif policy_mode == "responder_v6":
            # RESPONDER V6: STRICTLY SELECTIVE CONDITIONING
            
            # 1. LAND PREEMPTION: Gated strictly on opp_quads >= 2/3 + safe runway reserve
            if own_quads == 1 and 6 <= day <= 7 and opp_quads >= 2 and money >= 950.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            if own_quads == 2 and 8 <= day <= 11 and opp_quads >= 3 and money >= 1200.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            # 2. LIVESTOCK MATCHING: Strictly when opp_animals >= 5 (verified swarm) + $950 cash reserve
            if own_quads >= 2 and 8 <= day <= 15 and opp_animals >= 5:
                if own_cows < 8 and money >= 950.0 and own_animals < opp_animals:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                        mkt.append(["BUY_ANIMAL", "COW"])
                        
            # 3. SELECTIVE FEED ECONOMICS:
            # ONLY suppress open-market feed purchases IF wool is crashed (<$35) AND milk is low (<$50)
            # Never starve profitable cows producing $70+ milk!
            if day >= 22 and (p_wool < 35.0 and p_milk < 50.0):
                mkt = [m for m in mkt if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

        act["market"] = mkt
        return act

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    base_challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    base_challenger._V18_SELECTED_DAY = {0: None, 1: None}
    base_challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs_cand = env.state[cand_idx].observation
        act_cand = policy_agent(obs_cand)
        act_opp = opp_actions[s]
        
        actions = [None, None]
        actions[cand_idx] = act_cand
        actions[opp_idx] = act_opp
        env.step(actions)
        
    fin_cand = env.state[cand_idx].reward
    fin_opp = env.state[opp_idx].reward
    
    return os.path.basename(replay_file), opp_name, policy_mode, orig_cand_rew, orig_opp_rew, fin_cand, fin_opp

def main():
    print("=========================================================================================")
    print("     PARALLEL 12-WORKER HEAD-TO-HEAD: BASELINE vs RESPONDER V5 vs RESPONDER V6          ")
    print("=========================================================================================")
    
    targets = [
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 0), # vs RicardoLopez
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 0), # vs JZ
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json", 0), # vs ayman elamin
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 0), # vs Soumi Ghosh
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 0), # vs arao
        (r"D:\kaggriculture\topreply\loss\104499847.json", 1),                              # vs Crop Dusta
        (r"D:\kaggriculture\topreply\win\104492175.json", 1),                               # vs tetsuya 104492
        (r"D:\kaggriculture\topreply\win\103857429.json", 1),                               # vs tetsuya 103857
        (r"D:\kaggriculture\topreply\win\104514177.json", 1),                               # vs QQ Farming
        (r"D:\kaggriculture\topreply\win\104466724.json", 1),                               # vs islet
    ]
    
    modes = ["baseline", "responder_v5", "responder_v6"]
    tasks = [(fpath, p_idx, m) for fpath, p_idx in targets for m in modes]
    
    print(f"Evaluating {len(tasks)} counterfactual scenarios across 12 parallel workers...")
    t0 = time.time()
    
    results = {}
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_sim, t): t for t in tasks}
        for f in as_completed(futures):
            fname, opp_name, mode, orig_c, orig_o, fin_c, fin_o = f.result()
            key = (fname, opp_name)
            if key not in results: results[key] = {}
            results[key][mode] = (fin_c, fin_o)
            
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f}s\n")
    
    print("=" * 135)
    print(f"{'Replay Match':<28} | {'Baseline':<12} | {'Responder V5':<13} | {'Responder V6':<13} | {'V6 vs Base':<12} | {'V6 vs V5':<12} | Status")
    print("=" * 135)
    
    base_tot, v5_tot, v6_tot = 0.0, 0.0, 0.0
    for (fname, opp_name), data in sorted(results.items()):
        b_c, _ = data["baseline"]
        v5_c, _ = data["responder_v5"]
        v6_c, opp_rew = data["responder_v6"]
        base_tot += b_c
        v5_tot += v5_c
        v6_tot += v6_c
        d_base = v6_c - b_c
        d_v5 = v6_c - v5_c
        status = "WIN [W]" if v6_c > opp_rew else "LOSS"
        lbl = f"{fname[:10]} vs {opp_name[:14]}"
        print(f"{lbl:<28} | ${b_c:10,.0f} | ${v5_c:11,.0f} | ${v6_c:11,.0f} | {d_base:+10,.0f} | {d_v5:+10,.0f} | {status}")
        
    n = len(results)
    print("=" * 135)
    print(f"{'MEAN WEALTH ACROSS ALL 10':<28} | ${base_tot/n:10,.0f} | ${v5_tot/n:11,.0f} | ${v6_tot/n:11,.0f} | {v6_tot/n - base_tot/n:+10,.0f} | {v6_tot/n - v5_tot/n:+10,.0f} |")
    print("=" * 135)

if __name__ == "__main__":
    main()
