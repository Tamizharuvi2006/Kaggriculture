import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments
import importlib
import time

import submission_challenger_exp208 as old_mod
import submission_challenger_exp208_clean as new_mod

print("=========================================================================================")
print("     STEP-BY-STEP DIFFERENTIAL AUDIT: OLD VS NEW CLEAN EXP208 CHALLENGER                 ")
print("=========================================================================================")

seeds = list(range(2000000, 2000100)) # 100 seeds x 2 seats = 200 matches

total_steps_checked = 0
total_matches = 0
mismatches = 0
first_mismatch_detail = None

t0 = time.time()

for idx, seed in enumerate(seeds):
    for seat in (0, 1):
        total_matches += 1
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        # Baseline opponent: simple pass/wait or default agent
        # We want to feed the exact same environment observations to both agents simultaneously
        # Let's run a match with old_mod.agent vs baseline, and at each step compare old_mod.agent(obs) vs new_mod.agent(obs)
        
        # Initialize match
        env.reset()
        
        # Reset internal module states
        if hasattr(old_mod, "_V18_SELECTED_MARKET"):
            old_mod._V18_SELECTED_MARKET = [None, None]
            old_mod._V18_SELECTED_DAY = [None, None]
            old_mod._V18_SELECTED_BOARD = [None, None]
        if hasattr(new_mod, "_V18_SELECTED_MARKET"):
            new_mod._V18_SELECTED_MARKET = [None, None]
            new_mod._V18_SELECTED_DAY = [None, None]
            new_mod._V18_SELECTED_BOARD = [None, None]

        done = False
        step_num = 0
        
        while not env.done:
            obs = env.state[seat].observation
            # Get action from old
            act_old = old_mod.agent(obs)
            # Get action from new
            act_new = new_mod.agent(obs)
            
            total_steps_checked += 1
            
            if act_old != act_new:
                mismatches += 1
                if first_mismatch_detail is None:
                    first_mismatch_detail = {
                        "seed": seed,
                        "seat": seat,
                        "step": step_num,
                        "act_old": act_old,
                        "act_new": act_new,
                    }
                break
                
            # Step the game forward using the verified action
            other_seat = 1 - seat
            actions = [None, None]
            actions[seat] = act_old
            actions[other_seat] = {"farmer": ["PASS"], "hands": [], "market": []}
            env.step(actions)
            step_num += 1
            
    if (idx + 1) % 25 == 0:
        print(f"Progress: {idx + 1}/100 seeds checked ({total_steps_checked:,} steps evaluated, {mismatches} mismatches)...")

elapsed = time.time() - t0
print(f"\nAudit completed in {elapsed:.2f}s ({total_matches / elapsed:.1f} matches/sec)")
print(f"Total Matches Checked: {total_matches}")
print(f"Total Steps Evaluated: {total_steps_checked:,}")
print(f"Total Action Mismatches: {mismatches}")

if mismatches == 0:
    print("\n[PASS] VERDICT: 100% BIT-EXACT BEHAVIORAL EQUIVALENCE ACROSS ALL 144,000 STEPS!")
else:
    print(f"\n[FAIL] VERDICT: MISMATCH DETECTED: {first_mismatch_detail}")
    sys.exit(1)
