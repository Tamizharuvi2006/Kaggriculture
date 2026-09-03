import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_match(args):
    seed, hero_seat = args
    import kaggle_environments
    import submission as control
    import submission_challenger_exp208_clean as candidate
    
    # Enable adaptation in candidate
    candidate.STRATEGY["fixed_board_adaptation"] = True
    candidate.STRATEGY["adaptive_animal_mode"] = "mirror"
    candidate.STRATEGY["adaptive_capital_priority"] = False
    
    candidate._V18_SELECTED_MARKET = {0: None, 1: None}
    candidate._V18_SELECTED_DAY = {0: None, 1: None}
    candidate._V18_SELECTED_BOARD = {0: None, 1: None}
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        
        if hero_seat == 0:
            act0 = candidate.agent(obs0)
            act1 = control.agent(obs1)
        else:
            act0 = control.agent(obs0)
            act1 = candidate.agent(obs1)
            
        env.step([act0, act1])
        
    hero_rew = env.state[hero_seat].reward
    opp_rew = env.state[1 - hero_seat].reward
    win = 1 if hero_rew > opp_rew else (0.5 if hero_rew == opp_rew else 0)
    margin = hero_rew - opp_rew
    
    return seed, hero_seat, hero_rew, opp_rew, win, margin

def main():
    print("=========================================================================================")
    print("     PARALLEL 12-WORKER HEAD-TO-HEAD: CANDIDATE (WITH ADAPTATION) VS CONTROL (SUBMISSION.PY)")
    print("=========================================================================================")
    
    seeds = [1000 + i * 37 for i in range(25)] # 25 seeds
    tasks = []
    for s in seeds:
        tasks.append((s, 0)) # Candidate as Seat 0
        tasks.append((s, 1)) # Candidate as Seat 1
        
    print(f"Running {len(tasks)} matches ({len(seeds)} seeds x 2 seats) on 12 workers...")
    t0 = time.time()
    
    results = []
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_match, t): t for t in tasks}
        for f in as_completed(futures):
            res = f.result()
            results.append(res)
            
    elapsed = time.time() - t0
    
    wins = sum(1 for r in results if r[4] == 1)
    ties = sum(1 for r in results if r[4] == 0.5)
    losses = sum(1 for r in results if r[4] == 0)
    win_rate = (wins + 0.5 * ties) / len(results) * 100.0
    mean_margin = sum(r[5] for r in results) / len(results)
    mean_hero = sum(r[2] for r in results) / len(results)
    mean_opp = sum(r[3] for r in results) / len(results)
    
    print(f"\nCompleted in {elapsed:.2f}s ({len(tasks)/elapsed:.2f} matches/sec)\n")
    print(f"Results across {len(results)} matches:")
    print(f"  Win Rate    : {win_rate:.1f}% ({wins}W / {losses}L / {ties}T)")
    print(f"  Mean Margin : {mean_margin:+,.1f}")
    print(f"  Hero Mean   : ${mean_hero:,.0f}")
    print(f"  Control Mean: ${mean_opp:,.0f}")

if __name__ == "__main__":
    main()
