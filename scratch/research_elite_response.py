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
    
    # We replace target_player_idx with our candidate
    cand_idx = target_player_idx
    opp_idx = 1 - cand_idx
    
    cand_name = "Candidate"
    opp_name = agents[opp_idx].get("Name", f"Player {opp_idx}")
    orig_cand_rew = rewards[cand_idx]
    orig_opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    opp_actions = [frame[opp_idx].get("action") for frame in steps[1:]]
    
    # Define agent with policy_mode
    def policy_agent(obs):
        # Determine step
        step = obs.get("step") if isinstance(obs, dict) else getattr(obs, "step", None)
        if step is None:
            step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
        day = step // 24
        hour = step % 24
        
        farms = obs.get("farms", [{}, {}])
        own = farms[cand_idx] if len(farms) > cand_idx else {}
        opp = farms[opp_idx] if len(farms) > opp_idx else {}
        
        # Base act
        act = base_challenger.agent(obs)
        if not isinstance(act, dict): return act
        
        if policy_mode == "baseline":
            return act
            
        mkt = list(act.get("market") or [])
        money = float(own.get("money", 0) or 0)
        own_quads = len(own.get("unlocked_quadrants", []) or [])
        
        # Opponent visible state
        opp_quads = len(opp.get("unlocked_quadrants", []) or [])
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
        
        is_livestock_heavy = (day >= 1 and opp_animals >= 2) or (day >= 5 and opp_animals >= 4)
        
        if is_livestock_heavy:
            # 1. Early Land #2 Acceleration (Day 5-7 when cash >= 750)
            if own_quads == 1 and 5 <= day <= 7 and money >= 750.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            # 2. Early Land #3 Acceleration (Day 8-10 when cash >= 750)
            if own_quads == 2 and 8 <= day <= 10 and money >= 750.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
                    
            # 3. Aggressive Cow Matching on unlocked land (up to 8 cows)
            if own_animals < opp_animals and money >= 450.0 and own_cows < 8 and day <= 15:
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
    print("     PARALLEL 12-WORKER COUNTERFACTUAL LAB: ELITE-LIVESTOCK RESPONDER RESEARCH           ")
    print("=========================================================================================")
    
    # 7 elite replays (where target is opponent of tetsuya)
    elite_files = [
        (r"D:\kaggriculture\topreply\win\104514177.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\win\104492175.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\win\103857429.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\win\104466724.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\win\103850715.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\win\103837306.json", 1), # vs tetsuya
        (r"D:\kaggriculture\topreply\loss\104499847.json", 1), # vs tetsuya
    ]
    
    # 3 recent live losses (where target is Tamizharuvi)
    live_loss_files = [
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 0), # vs arao
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 0), # vs RicardoLopez
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 0), # vs JZ
    ]
    
    all_targets = elite_files + live_loss_files
    modes = ["baseline", "elite_responder"]
    
    tasks = []
    for fpath, p_idx in all_targets:
        for m in modes:
            tasks.append((fpath, p_idx, m))
            
    print(f"Running {len(tasks)} counterfactual simulations across 12 parallel workers...")
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
    
    print("=" * 115)
    print(f"{'Replay Match':<35} | {'Baseline Cand':<14} | {'Responder Cand':<15} | {'Cand Gain ($)':<14} | {'Opponent ($)':<14} | Result")
    print("=" * 115)
    
    tot_base = 0.0
    tot_resp = 0.0
    
    for (fname, opp_name), data in sorted(results.items()):
        b_c, b_o = data["baseline"]
        r_c, r_o = data["elite_responder"]
        tot_base += b_c
        tot_resp += r_c
        gain = r_c - b_c
        status = "WIN" if r_c > r_o else "LOSS"
        match_label = f"{fname[:14]} vs {opp_name[:15]}"
        print(f"{match_label:<35} | ${b_c:12,.0f} | ${r_c:13,.0f} | {gain:+12,.0f} | ${r_o:12,.0f} | {status}")
        
    n = len(results)
    print("=" * 115)
    print(f"Mean Baseline Candidate Wealth : ${tot_base / n:,.0f}")
    print(f"Mean Responder Candidate Wealth: ${tot_resp / n:,.0f}")
    print(f"Net Average Gain from Responder: {tot_resp / n - tot_base / n:+,.0f}")
    print("=" * 115)

if __name__ == "__main__":
    main()
