import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_sim(args):
    ep_file, adapt_enabled, mode, prioritize = args
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
    
    challenger.STRATEGY["fixed_board_adaptation"] = adapt_enabled
    challenger.STRATEGY["adaptive_animal_mode"] = mode
    challenger.STRATEGY["adaptive_capital_priority"] = prioritize
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    challenger._V18_SELECTED_DAY = {0: None, 1: None}
    challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs_hero = env.state[hero_idx].observation
        act_hero = challenger.agent(obs_hero)
        act_opp = opp_actions[s]
        
        actions = [None, None]
        actions[hero_idx] = act_hero
        actions[opp_idx] = act_opp
        env.step(actions)
        
    fin_h = env.state[hero_idx].reward
    fin_o = env.state[opp_idx].reward
    
    return eid, adapt_enabled, mode, prioritize, orig_h, orig_o, fin_h, fin_o

def main():
    import glob
    ep_files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")
    print(f"Loaded {len(ep_files)} live loss replays.")
    
    configs = [
        (False, "mirror", False), # Disabled (Baseline)
        (True, "mirror", False),  # Mirror
        (True, "diversify", False), # Diversify
        (True, "mirror", True),   # Mirror + Capital Priority
        (True, "diversify", True), # Diversify + Capital Priority
    ]
    
    tasks = []
    for ep in ep_files:
        for c in configs:
            tasks.append((ep, c[0], c[1], c[2]))
            
    print(f"Evaluating {len(tasks)} scenarios across 12 parallel workers...")
    t0 = time.time()
    
    results = {}
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_sim, t): t for t in tasks}
        for f in as_completed(futures):
            eid, a_en, mode, prio, orig_h, orig_o, fin_h, fin_o = f.result()
            cfg = (a_en, mode, prio)
            if cfg not in results: results[cfg] = []
            results[cfg].append({"eid": eid, "orig_h": orig_h, "orig_o": orig_o, "fin_h": fin_h, "fin_o": fin_o, "gain": fin_h - orig_h, "margin": fin_h - fin_o})
            
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f}s\n")
    
    print("=" * 115)
    print(f"{'Config (AdaptEnabled, Mode, CapitalPriority)':>45} | {'Original Mean ($)':>18} | {'Counterfactual ($)':>18} | {'Net Gain ($)':>15} | {'Win Count':>10}")
    print("=" * 115)
    
    for cfg in configs:
        matches = results[cfg]
        mean_orig = sum(m["orig_h"] for m in matches) / len(matches)
        mean_fin = sum(m["fin_h"] for m in matches) / len(matches)
        net_gain = mean_fin - mean_orig
        wins = sum(1 for m in matches if m["fin_h"] > m["fin_o"])
        cfg_str = f"Adapt={cfg[0]}, Mode={cfg[1]}, Prio={cfg[2]}"
        print(f"{cfg_str:>45} | ${mean_orig:16,.0f} | ${mean_fin:16,.0f} | ${net_gain:+13,.0f} | {wins:2d}/{len(matches)} W")

if __name__ == "__main__":
    main()
