import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_match(args):
    seed, v4_seat = args
    import kaggle_environments
    import submission_challenger_exp208_clean as base_bot
    
    # We define V4 agent wrapper
    def v4_agent(obs):
        step = obs.get("step") if isinstance(obs, dict) else getattr(obs, "step", None)
        if step is None:
            step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
        day = step // 24
        hour = step % 24
        
        farms = obs.get("farms", [{}, {}])
        own = farms[v4_seat] if len(farms) > v4_seat else {}
        opp = farms[1 - v4_seat] if len(farms) > (1 - v4_seat) else {}
        
        act = base_bot.agent(obs)
        if not isinstance(act, dict): return act
        
        mkt = list(act.get("market") or [])
        money = float(own.get("money", 0) or 0)
        own_quads = len(own.get("unlocked_quadrants", []) or [])
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
        
        # 1. Opponent-Land Preemption
        if own_quads == 1 and 5 <= day <= 7 and opp_quads >= 2 and money >= 750.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                mkt.insert(0, ["BUY_LAND"])
                
        if own_quads == 2 and 8 <= day <= 11 and opp_quads >= 3 and money >= 750.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                mkt.insert(0, ["BUY_LAND"])
                
        # 2. Livestock scaling match
        if own_quads >= 2 and own_animals < opp_animals and opp_animals >= 4 and money >= 550.0 and own_cows < 8 and day <= 15:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                mkt.append(["BUY_ANIMAL", "COW"])
                
        act["market"] = mkt
        return act

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    base_bot._V18_SELECTED_MARKET = {0: None, 1: None}
    base_bot._V18_SELECTED_DAY = {0: None, 1: None}
    base_bot._V18_SELECTED_BOARD = {0: None, 1: None}
    
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        
        if v4_seat == 0:
            act0 = v4_agent(obs0)
            act1 = base_bot.agent(obs1)
        else:
            act0 = base_bot.agent(obs0)
            act1 = v4_agent(obs1)
            
        env.step([act0, act1])
        
    v4_reward = env.state[v4_seat].reward
    base_reward = env.state[1 - v4_seat].reward
    
    win = 1 if v4_reward > base_reward else (0.5 if v4_reward == base_reward else 0)
    delta = v4_reward - base_reward
    
    return seed, v4_seat, v4_reward, base_reward, win, delta

def main():
    print("=========================================================================================")
    print("     500-MATCH COMPREHENSIVE TOURNAMENT: RESPONDER V4 vs LIVE CLEAN CANDIDATE            ")
    print("=========================================================================================")
    
    # 250 fresh seeds x 2 seats = 500 matches
    seeds = [3000000 + i * 17 for i in range(250)]
    tasks = []
    for s in seeds:
        tasks.append((s, 0)) # V4 as Seat 0
        tasks.append((s, 1)) # V4 as Seat 1
        
    print(f"Executing {len(tasks)} matches ({len(seeds)} fresh seeds x 2 seats) on 12 parallel workers...")
    t0 = time.time()
    
    results = []
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_match, t): t for t in tasks}
        for f in as_completed(futures):
            results.append(f.result())
            if len(results) % 50 == 0:
                print(f"  Progress: {len(results)}/{len(tasks)} matches completed...")
                
    elapsed = time.time() - t0
    
    v4_scores = [r[2] for r in results]
    base_scores = [r[3] for r in results]
    deltas = [r[5] for r in results]
    
    wins = sum(1 for r in results if r[4] == 1)
    ties = sum(1 for r in results if r[4] == 0.5)
    losses = sum(1 for r in results if r[4] == 0)
    win_rate = (wins + 0.5 * ties) / len(results) * 100.0
    
    mean_v4 = np.mean(v4_scores)
    mean_base = np.mean(base_scores)
    mean_delta = np.mean(deltas)
    
    tail_v4_5th = np.percentile(v4_scores, 5)
    tail_base_5th = np.percentile(base_scores, 5)
    
    regressions = sum(1 for d in deltas if d < 0)
    neutral = sum(1 for d in deltas if d == 0)
    improvements = sum(1 for d in deltas if d > 0)
    
    # Seat-specific breakdown
    s0_results = [r for r in results if r[1] == 0]
    s1_results = [r for r in results if r[1] == 1]
    
    s0_wr = (sum(1 for r in s0_results if r[4] == 1) + 0.5 * sum(1 for r in s0_results if r[4] == 0.5)) / len(s0_results) * 100.0
    s1_wr = (sum(1 for r in s1_results if r[4] == 1) + 0.5 * sum(1 for r in s1_results if r[4] == 0.5)) / len(s1_results) * 100.0
    
    print("\n" + "=" * 95)
    print("                    500-MATCH HEAD-TO-HEAD VALIDATION SUMMARY                            ")
    print("=" * 95)
    print(f"Completed in           : {elapsed:.2f}s ({len(tasks)/elapsed:.1f} matches/sec)")
    print(f"Overall Win Rate       : {win_rate:.1f}% ({wins}W / {losses}L / {ties}T)")
    print(f"Seat 0 (First Mover)   : {s0_wr:.1f}% Win Rate")
    print(f"Seat 1 (Second Mover)  : {s1_wr:.1f}% Win Rate")
    print(f"Mean Wealth (V4)       : ${mean_v4:,.0f}")
    print(f"Mean Wealth (Live Base): ${mean_base:,.0f}")
    print(f"Net Delta per Game     : {mean_delta:+,.0f}")
    print(f"Tail Floor (5th %ile)  : V4 ${tail_v4_5th:,.0f} vs Baseline ${tail_base_5th:,.0f} (Delta: {tail_v4_5th - tail_base_5th:+,.0f})")
    print(f"Distribution           : {improvements} Improvements / {neutral} Neutral / {regressions} Regressions")
    print("=" * 95)

if __name__ == "__main__":
    main()
