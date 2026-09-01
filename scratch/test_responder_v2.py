import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_counterfactual(args):
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
        
        # Opponent visible state
        opp_quads = len(opp.get("unlocked_quadrants", []) or [])
        opp_workers = len(opp.get("hands", []) or [])
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
        
        if policy_mode == "responder_v1":
            # Responder v1: blunt trigger, $750 buffer
            is_heavy = (day >= 1 and opp_animals >= 2) or (day >= 5 and opp_animals >= 4)
            land_thresh = 750.0
            cow_thresh = 450.0
        elif policy_mode == "responder_v2":
            # Responder v2: strict composite signature, $950 safety buffer
            # Fingerprint: Opponent has scaled >=3 animals AND >=4 workers (the canonical livestock rush)
            is_heavy = (day >= 1 and opp_animals >= 3 and opp_workers >= 4) or \
                       (day >= 4 and opp_animals >= 4) or \
                       (day >= 7 and opp_animals >= 6)
            land_thresh = 950.0  # $750 land cost + $200 working capital buffer
            cow_thresh = 600.0   # $450 cow cost + $150 feed/wage buffer
        else:
            return act
            
        if is_heavy:
            # 1. Early Land #2 Acceleration (Days 5-7 with safety buffer)
            if own_quads == 1 and 5 <= day <= 7 and money >= land_thresh:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            # 2. Early Land #3 Acceleration (Days 8-10 with safety buffer)
            # Only trigger Q3 if opponent also opened Q2 or has >= 5 animals
            if own_quads == 2 and 8 <= day <= 10 and money >= land_thresh and (opp_quads >= 2 or opp_animals >= 5):
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            # 3. Controlled Cow Matching (only when safe cash buffer exists)
            if own_animals < opp_animals and money >= cow_thresh and own_cows < 8 and day <= 15:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                    mkt.append(["BUY_ANIMAL", "COW"])
                    
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
    print("     PARALLEL 12-WORKER HEAD-TO-HEAD: BASELINE vs RESPONDER V1 vs RESPONDER V2          ")
    print("=========================================================================================")
    
    targets = [
        (r"D:\kaggriculture\topreply\loss\104499847.json", 1), # vs Crop Dusta
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 0), # vs JZ
        (r"D:\kaggriculture\topreply\win\103850715.json", 1), # vs tetsuya 103850
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 0), # vs arao
        (r"D:\kaggriculture\topreply\win\104466724.json", 1), # vs islet
        (r"D:\kaggriculture\topreply\win\103837306.json", 1), # vs tetsuya 103837
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 0), # vs RicardoLopez
        (r"D:\kaggriculture\topreply\win\103857429.json", 1), # vs tetsuya 103857 (V1 Regression)
        (r"D:\kaggriculture\topreply\win\104514177.json", 1), # vs QQ Farming (V1 Regression)
        (r"D:\kaggriculture\topreply\win\104492175.json", 1), # vs tetsuya 104492 (V1 Major Regression)
    ]
    
    modes = ["baseline", "responder_v1", "responder_v2"]
    tasks = [(fpath, p_idx, m) for fpath, p_idx in targets for m in modes]
    
    print(f"Evaluating {len(tasks)} counterfactual scenarios across 12 parallel workers...")
    t0 = time.time()
    
    results = {}
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_counterfactual, t): t for t in tasks}
        for f in as_completed(futures):
            fname, opp_name, mode, orig_c, orig_o, fin_c, fin_o = f.result()
            key = (fname, opp_name)
            if key not in results: results[key] = {}
            results[key][mode] = (fin_c, fin_o)
            
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f}s\n")
    
    print("=" * 125)
    print(f"{'Replay Match':<30} | {'Baseline':<12} | {'Responder V1':<13} | {'Responder V2':<13} | {'V2 vs Base':<12} | {'V2 vs V1':<12} | Status")
    print("=" * 125)
    
    base_tot, v1_tot, v2_tot = 0.0, 0.0, 0.0
    for (fname, opp_name), data in sorted(results.items()):
        b_c, _ = data["baseline"]
        v1_c, _ = data["responder_v1"]
        v2_c, opp_rew = data["responder_v2"]
        base_tot += b_c
        v1_tot += v1_c
        v2_tot += v2_c
        d_base = v2_c - b_c
        d_v1 = v2_c - v1_c
        status = "WIN 🏆" if v2_c > opp_rew else "LOSS"
        lbl = f"{fname[:12]} vs {opp_name[:12]}"
        print(f"{lbl:<30} | ${b_c:10,.0f} | ${v1_c:11,.0f} | ${v2_c:11,.0f} | {d_base:+10,.0f} | {d_v1:+10,.0f} | {status}")
        
    n = len(results)
    print("=" * 125)
    print(f"{'MEAN WEALTH ACROSS ALL 10':<30} | ${base_tot/n:10,.0f} | ${v1_tot/n:11,.0f} | ${v2_tot/n:11,.0f} | {v2_tot/n - base_tot/n:+10,.0f} | {v2_tot/n - v1_tot/n:+10,.0f} |")
    print("=" * 125)

if __name__ == "__main__":
    main()
