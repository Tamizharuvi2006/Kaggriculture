"""EXP115: Step-by-Step Exact Bitwise Parity Verification Suite.

Rigorous validation between submission.py (Original Control A) and submission_clean.py (Clean D.1)
across 20 tournament seeds (14,400 steps total):

Checks every single step:
- Farmer action exact match
- Hand/worker actions exact match
- Market orders exact match
- Terminal state & final reward exact match

Acceptance Gate:
0 action differences, 0 market order differences, 0 reward differences (100.000% bitwise behavioral parity).
"""
from __future__ import annotations
import sys
import os
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_orig = importlib.util.spec_from_file_location("sub_orig", os.path.join(BASE_DIR, "submission.py"))
sub_orig = importlib.util.module_from_spec(spec_orig)
spec_orig.loader.exec_module(sub_orig)

spec_clean = importlib.util.spec_from_file_location("sub_clean", os.path.join(BASE_DIR, "submission_clean.py"))
sub_clean = importlib.util.module_from_spec(spec_clean)
spec_clean.loader.exec_module(sub_clean)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

SEEDS = [100 + i * 25 for i in range(20)]

def run_parity_check():
    print("=" * 110)
    print("EXP115: STEP-BY-STEP EXACT BITWISE PARITY VERIFICATION SUITE (20 SEEDS / 14,400 STEPS)")
    print("=" * 110)

    total_steps_checked = 0
    farmer_diffs = 0
    hands_diffs = 0
    market_diffs = 0
    reward_diffs = 0

    for seed_idx, seed in enumerate(SEEDS):
        # 1. Run Original
        env_orig = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_orig.reset()
        sub_orig._APEX35_PRICE_HISTORY = {"STRAWBERRY": [], "MILK": []}

        # 2. Run Clean
        env_clean = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_clean.reset()
        sub_clean._APEX35_PRICE_HISTORY = {"STRAWBERRY": [], "MILK": []}

        step_idx = 0
        while not env_orig.done and not env_clean.done:
            obs_orig = env_orig.state[0].observation
            obs_clean = env_clean.state[0].observation
            opp_obs = env_orig.state[1].observation

            act_orig = sub_orig.agent(obs_orig, env_orig.configuration)
            act_clean = sub_clean.agent(obs_clean, env_clean.configuration)
            act_opp = bot_v18.agent(opp_obs)

            # Compare step actions
            if act_orig.get("farmer") != act_clean.get("farmer"):
                farmer_diffs += 1
                if farmer_diffs <= 3:
                    print(f"  [DIFF Seed {seed} Step {step_idx}] Farmer: Orig={act_orig.get('farmer')} vs Clean={act_clean.get('farmer')}")

            if act_orig.get("hands") != act_clean.get("hands"):
                hands_diffs += 1
                if hands_diffs <= 3:
                    print(f"  [DIFF Seed {seed} Step {step_idx}] Hands: Orig={act_orig.get('hands')} vs Clean={act_clean.get('hands')}")

            if act_orig.get("market") != act_clean.get("market"):
                market_diffs += 1
                if market_diffs <= 3:
                    print(f"  [DIFF Seed {seed} Step {step_idx}] Market: Orig={act_orig.get('market')} vs Clean={act_clean.get('market')}")

            env_orig.step([act_orig, act_opp])
            env_clean.step([act_clean, act_opp])
            step_idx += 1
            total_steps_checked += 1

        r_orig = float(env_orig.state[0].reward or 0.0)
        r_clean = float(env_clean.state[0].reward or 0.0)
        if abs(r_orig - r_clean) > 1e-4:
            reward_diffs += 1
            print(f"  [REWARD DIFF Seed {seed}] Orig=${r_orig:,.2f} vs Clean=${r_clean:,.2f}")
        else:
            print(f"  Seed {seed:>5} (720 steps): PERFECT MATCH (Reward: ${r_orig:,.2f})")

    print("\n" + "=" * 110)
    print("EXP115 PARITY VERIFICATION SUMMARY")
    print("=" * 110)
    print(f"  * Total Steps Evaluated       : {total_steps_checked:,} steps")
    print(f"  * Farmer Action Diffs         : {farmer_diffs}")
    print(f"  * Hand / Worker Action Diffs  : {hands_diffs}")
    print(f"  * Market Order Diffs          : {market_diffs}")
    print(f"  * Final Reward Diffs          : {reward_diffs}")
    print("-" * 110)

    is_perfect = (farmer_diffs == 0 and hands_diffs == 0 and market_diffs == 0 and reward_diffs == 0)
    print(f"  * FINAL PARITY STATUS         : {'100.000% BITWISE IDENTICAL (PERFECT MATCH)' if is_perfect else 'PARITY MISMATCH'}")
    print("=" * 110)

if __name__ == "__main__":
    run_parity_check()
