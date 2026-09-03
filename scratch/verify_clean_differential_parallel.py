import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_differential_seed(seed):
    import kaggle_environments
    import submission_challenger_exp208 as old_mod
    import submission_challenger_exp208_clean as new_mod
    
    steps_checked = 0
    mismatches = 0
    mismatch_detail = None
    
    for seat in (0, 1):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        
        # Reset internal module states
        old_mod._V18_SELECTED_MARKET = {0: None, 1: None}
        old_mod._V18_SELECTED_DAY = {0: None, 1: None}
        old_mod._V18_SELECTED_BOARD = {0: None, 1: None}
        
        new_mod._V18_SELECTED_MARKET = {0: None, 1: None}
        new_mod._V18_SELECTED_DAY = {0: None, 1: None}
        new_mod._V18_SELECTED_BOARD = {0: None, 1: None}
        
        step_num = 0
        while not env.done:
            obs = env.state[seat].observation
            act_old = old_mod.agent(obs)
            act_new = new_mod.agent(obs)
            
            steps_checked += 1
            if act_old != act_new:
                mismatches += 1
                mismatch_detail = {
                    "seed": seed,
                    "seat": seat,
                    "step": step_num,
                    "act_old": act_old,
                    "act_new": act_new,
                }
                return steps_checked, mismatches, mismatch_detail
                
            other_seat = 1 - seat
            actions = [None, None]
            actions[seat] = act_old
            actions[other_seat] = {"farmer": ["PASS"], "hands": [], "market": []}
            env.step(actions)
            step_num += 1
            
    return steps_checked, mismatches, mismatch_detail

def main():
    print("=========================================================================================")
    print("     PARALLEL 12-WORKER STEP-BY-STEP DIFFERENTIAL AUDIT: OLD VS NEW CLEAN EXP208         ")
    print("=========================================================================================")
    
    seeds = list(range(2000000, 2000100)) # 100 seeds x 2 seats = 200 matches
    
    t0 = time.time()
    total_steps = 0
    total_mismatches = 0
    first_mismatch = None
    
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(run_differential_seed, seed): seed for seed in seeds}
        done_count = 0
        for fut in as_completed(futures):
            steps, mismatches, detail = fut.result()
            total_steps += steps
            total_mismatches += mismatches
            if mismatches > 0 and first_mismatch is None:
                first_mismatch = detail
            done_count += 1
            if done_count % 25 == 0 or done_count == len(seeds):
                print(f"Progress: {done_count}/100 seeds evaluated ({total_steps:,} steps)...")
                
    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.2f}s (12 workers: {len(seeds)*2 / elapsed:.1f} matches/sec)")
    print(f"Total Matches Checked: {len(seeds)*2}")
    print(f"Total Steps Evaluated: {total_steps:,}")
    print(f"Total Action Mismatches: {total_mismatches}")
    
    if total_mismatches == 0:
        print("\n[PASS] VERDICT: 100% BIT-EXACT BEHAVIORAL EQUIVALENCE ACROSS ALL 144,000 STEPS!")
    else:
        print(f"\n[FAIL] VERDICT: MISMATCH DETECTED: {first_mismatch}")
        sys.exit(1)

if __name__ == "__main__":
    main()
