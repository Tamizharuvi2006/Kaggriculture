"""Candidate L+ Code Equivalence Verification Test.

Evaluates clean submission_candidate_l_plus.py against submission_candidate_l_plus_raw_backup.py
across 5 identical seeds to confirm 100% action and reward identity before declaring cleanup safe.
"""

import sys
import os
import importlib.util

if r"D:\kaggriculture" not in sys.path:
    sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments

CLEAN_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"
BACKUP_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus_raw_backup.py"
V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print("=" * 95, flush=True)
    print(" CANDIDATE L+ CLEANUP CODE EQUIVALENCE VERIFICATION TEST", flush=True)
    print("=" * 95, flush=True)

    clean_mod = _load_mod("clean_mod", CLEAN_PATH)
    backup_mod = _load_mod("backup_mod", BACKUP_PATH)
    opp_mod = _load_mod("v18_opp", V18_PATH)

    all_identical = True

    for seed in range(6000, 6005):
        # Run Clean Candidate L+ vs V18 Master
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state1 = env1.run([clean_mod.agent, opp_mod.agent])
        clean_wealth = state1[-1][0]["observation"]["farms"][0]["money"]

        # Run Backup Candidate L+ vs V18 Master
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state2 = env2.run([backup_mod.agent, opp_mod.agent])
        backup_wealth = state2[-1][0]["observation"]["farms"][0]["money"]

        actions_match = True
        for step_idx in range(len(state1)):
            act1 = state1[step_idx][0].get("action")
            act2 = state2[step_idx][0].get("action")
            if act1 != act2:
                actions_match = False
                break

        identical = (clean_wealth == backup_wealth) and actions_match
        if not identical:
            all_identical = False

        status_str = "100% IDENTICAL" if identical else "MISMATCH"
        print(f" Seed {seed:4d} | Clean Wealth: ${clean_wealth:9.2f} | Backup Wealth: ${backup_wealth:9.2f} | Status: {status_str}", flush=True)

    print("\n" + "=" * 95, flush=True)
    if all_identical:
        print(" SUCCESS: Cleaned Candidate L+ produces 100% IDENTICAL actions & rewards to backup!", flush=True)
        print(" Cleanup verified SAFE for production Kaggle upload.", flush=True)
    else:
        print(" WARNING: Mismatch detected between cleaned version and backup!", flush=True)
    print("=" * 95, flush=True)


if __name__ == "__main__":
    main()
