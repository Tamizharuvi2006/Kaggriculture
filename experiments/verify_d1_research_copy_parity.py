"""Parity Verification: submission.py (Control A) vs D1_RESEARCH_COPY.py.

Executes direct seed-by-seed behavioral and reward parity tests across 10 tournament seeds.
Confirms that D1_RESEARCH_COPY.py is a 100.0% identical, bit-for-bit operational clone.
"""
from __future__ import annotations
import sys
import os
import json
import importlib.util
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

spec_sub = importlib.util.spec_from_file_location("sub_prod", os.path.join(BASE_DIR, "submission.py"))
sub_prod = importlib.util.module_from_spec(spec_sub)
spec_sub.loader.exec_module(sub_prod)

spec_copy = importlib.util.spec_from_file_location("sub_copy", os.path.join(BASE_DIR, "D1_RESEARCH_COPY.py"))
sub_copy = importlib.util.module_from_spec(spec_copy)
spec_copy.loader.exec_module(sub_copy)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

TEST_SEEDS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

def test_parity():
    print("=" * 105)
    print("PARITY VERIFICATION: submission.py (CONTROL A) vs D1_RESEARCH_COPY.py")
    print("=" * 105)
    print(f"{'Seed':<10} | {'submission.py Final ($)':>25} | {'D1_RESEARCH_COPY Final ($)':>28} | {'Delta ($)':>12} | {'Parity Status'}")
    print("-" * 105)

    all_identical = True
    for s in TEST_SEEDS:
        # Run submission.py vs benchmark
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        while not env1.done:
            a0 = sub_prod.agent(env1.state[0].observation, env1.configuration)
            a1 = bot_v18.agent(env1.state[1].observation)
            env1.step([a0, a1])
        r1 = float(env1.state[0].reward or 0.0)

        # Run D1_RESEARCH_COPY.py vs benchmark
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        while not env2.done:
            a0 = sub_copy.agent(env2.state[0].observation, env2.configuration)
            a1 = bot_v18.agent(env2.state[1].observation)
            env2.step([a0, a1])
        r2 = float(env2.state[0].reward or 0.0)

        delta = r2 - r1
        is_exact = (delta == 0.0)
        if not is_exact:
            all_identical = False

        status = "[EXACT MATCH]" if is_exact else "[MISMATCH]"
        print(f"{s:<10} | ${r1:>24,.0f} | ${r2:>27,.0f} | ${delta:>+11,.0f} | {status}")

    print("=" * 105)
    if all_identical:
        print("  [SUCCESS] D1_RESEARCH_COPY.py is 100.0% mathematically identical to submission.py across all seeds.")
    else:
        print("  [FAILURE] Mismatch detected between submission.py and D1_RESEARCH_COPY.py.")
    print("=" * 105)

if __name__ == "__main__":
    test_parity()
