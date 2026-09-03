import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

import json
import time

def run_single(args):
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
    
    opp_name = agents[opp_idx].get("Name", f"Player {opp_idx}") if len(agents) > opp_idx else f"Player {opp_idx}"
    orig_cand_rew = rewards[cand_idx] if len(rewards) > cand_idx else 0.0
    orig_opp_rew = rewards[opp_idx] if len(rewards) > opp_idx else 0.0
    
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
        
        mkt = list(act.get("market") or [])
        money = float(own.get("money", 0) or 0)
        own_quads = len(own.get("unlocked_quadrants", []) or [])
        opp_quads = len(opp.get("unlocked_quadrants", []) or [])
        
        mkt_info = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt_info.get("prices") or {}
        p_wheat = float(prices.get("WHEAT", 25.0) or 25.0)
        p_wool = float(prices.get("WOOL", 180.0) or 180.0)
        p_milk = float(prices.get("MILK", 80.0) or 80.0)
        
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
        
        if policy_mode == "v6_baseline":
            # Exact V6 logic
            if own_quads == 1 and 6 <= day <= 7 and opp_quads >= 2 and money >= 950.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            if own_quads == 2 and 8 <= day <= 11 and opp_quads >= 3 and money >= 1200.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            if own_quads >= 2 and 8 <= day <= 15 and opp_animals >= 5:
                if own_cows < 8 and money >= 950.0 and own_animals < opp_animals:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                        mkt.append(["BUY_ANIMAL", "COW"])
            if day >= 22 and (p_wool < 35.0 and p_milk < 50.0):
                mkt = [m for m in mkt if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

        elif policy_mode == "v7_governor":
            # 1. Land preemption
            if own_quads == 1 and 6 <= day <= 7 and opp_quads >= 2 and money >= 950.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            if own_quads == 2 and 8 <= day <= 11 and opp_quads >= 3 and money >= 1200.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])
            # Lift Q4 limit if very wealthy
            if own_quads == 3 and 12 <= day <= 18 and opp_quads >= 3 and money >= 2500.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt):
                    mkt.insert(0, ["BUY_LAND"])

            # 2. Conservative livestock matching
            if own_quads >= 2 and 8 <= day <= 15 and opp_animals >= 5:
                if own_cows < 8 and money >= 950.0 and own_animals < opp_animals:
                    if p_milk >= p_wheat * 1.5:  # Only buy animals if milk is strongly profitable!
                        if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in mkt):
                            mkt.append(["BUY_ANIMAL", "COW"])

            # 3. Dynamic Feed Governor (From Day 8 onwards!)
            if day >= 8:
                # If milk is less than feed cost, buying feed loses cash every hour!
                milk_unprofitable = (p_milk < p_wheat * 1.15)
                wool_unprofitable = (p_wool < p_wheat * 1.15)
                
                # Check if market feed purchase should be suppressed
                if (milk_unprofitable and (own_sheep == 0 or wool_unprofitable)) or p_wheat >= 36.0:
                    mkt = [m for m in mkt if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

            # 4. On-Farm Cheap Feed Opportunity (Wheat seeds cost $10 for 6 wheat = $1.67/feed!)
            if 6 <= day <= 18 and p_wheat >= 30.0 and money >= 250.0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_SEED" and m[1] == "WHEAT" for m in mkt):
                    mkt.append(["BUY_SEED", "WHEAT", 3])

        # Enforce land bounds (cap at 4, not 3)
        final_orders = []
        for m in mkt:
            if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND":
                if own_quads >= 4:
                    continue
            final_orders.append(m)

        act["market"] = final_orders
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
    print("     COUNTERFACTUAL REPLAY HARNESS: RESPONDER V6 vs V7 DYNAMIC GOVERNOR                   ")
    print("=========================================================================================")
    
    targets = [
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 0), # vs RicardoLopez ($72.9k vs $29.7k)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 0), # vs JZ ($103.2k vs $64.2k)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json", 0), # vs ayman elamin ($104.0k vs $75.0k)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 0), # vs Soumi Ghosh ($57.0k vs $30.1k)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 0), # vs arao ($55.1k vs $40.6k)
    ]
    
    for replay_path, cand_seat in targets:
        print(f"\n--- Testing Replay: {os.path.basename(replay_path)} ---")
        _, opp_name, _, orig_cand, orig_opp, v6_cand, v6_opp = run_single((replay_path, cand_seat, "v6_baseline"))
        _, _, _, _, _, v7_cand, v7_opp = run_single((replay_path, cand_seat, "v7_governor"))
        
        delta_v6 = v6_cand - v6_opp
        delta_v7 = v7_cand - v7_opp
        improvement = v7_cand - v6_cand
        
        print(f"Opponent: {opp_name}")
        print(f"  Live Recorded Score : Hero ${orig_cand:,.0f} vs Opp ${orig_opp:,.0f} (Margin: ${orig_cand - orig_opp:+,.0f})")
        print(f"  V6 Baseline Counter : Hero ${v6_cand:,.0f} vs Opp ${v6_opp:,.0f} (Margin: ${delta_v6:+,.0f})")
        print(f"  V7 Governor Counter : Hero ${v7_cand:,.0f} vs Opp ${v7_opp:,.0f} (Margin: ${delta_v7:+,.0f})")
        print(f"  >>> V7 Cash Lift over V6: ${improvement:+,.0f} <<<")

if __name__ == "__main__":
    main()
