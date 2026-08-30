"""EXP163 Deep Forensic Analysis of Step 71 Fertilizer Divergence."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def test_fertilizer_counterfactual(seed: int, seat: int):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    # Baseline D.1
    env_base = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_base.reset()
    while not env_base.done:
        obs0 = env_base.state[0].observation if seat == 0 else env_base.state[1].observation
        obs1 = env_base.state[1].observation if seat == 0 else env_base.state[0].observation
        a0 = sub_d1.agent(obs0, env_base.configuration)
        try: a1 = opp_fn(obs1, env_base.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env_base.step([a0, a1] if seat == 0 else [a1, a0])

    r_base0 = float(env_base.state[seat].reward or 0.0)
    r_base1 = float(env_base.state[1 - seat].reward or 0.0)
    base_margin = r_base0 - r_base1

    # Counterfactual: Suppress fertilizer selling at Step 71 (Retain Fertilizer like V18)
    env_cf = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_cf.reset()
    while not env_cf.done:
        step = env_cf.state[0].observation.get("step", 0)
        obs0 = env_cf.state[0].observation if seat == 0 else env_cf.state[1].observation
        obs1 = env_cf.state[1].observation if seat == 0 else env_cf.state[0].observation

        a0 = sub_d1.agent(obs0, env_cf.configuration)
        # If selling fertilizer at step 71, remove that order
        if step == 71 and isinstance(a0, dict):
            m = a0.get("market", []) or []
            new_m = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "FERTILIZER")]
            a0["market"] = new_m

        try: a1 = opp_fn(obs1, env_cf.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env_cf.step([a0, a1] if seat == 0 else [a1, a0])

    r_cf0 = float(env_cf.state[seat].reward or 0.0)
    r_cf1 = float(env_cf.state[1 - seat].reward or 0.0)
    cf_margin = r_cf0 - r_cf1

    return {
        "seed": seed, "seat": seat,
        "base_hero": r_base0, "base_opp": r_base1, "base_margin": base_margin, "base_won": r_base0 > r_base1,
        "cf_hero": r_cf0, "cf_opp": r_cf1, "cf_margin": cf_margin, "cf_won": r_cf0 > r_cf1,
        "delta_margin": cf_margin - base_margin,
    }

def main():
    print("=" * 145)
    print("EXP163: STEP 71 FERTILIZER DIVERGENCE FORENSIC PROOF (20 SEEDS VS V18)")
    print("=" * 145)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]
    
    results = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1
        res = test_fertilizer_counterfactual(seed, seat)
        results.append(res)
        w_str = "FLIPPED TO WIN! 🏆" if (not res["base_won"] and res["cf_won"]) else ("WIN" if res["cf_won"] else "LOSS")
        print(f"Seed {seed:5d} (Seat {seat}): Base Margin: ${res['base_margin']:+10,.2f} -> CF Margin: ${res['cf_margin']:+10,.2f} (Delta: ${res['delta_margin']:+10,.2f}) | {w_str}")

    mean_delta = np.mean([r["delta_margin"] for r in results])
    cf_wins = sum(1 for r in results if r["cf_won"])
    print("=" * 145)
    print(f"SUMMARY: Counterfactual Fertilizer Retention Win Rate: {cf_wins}/20 ({cf_wins/20*100:.1f}%) | Mean Delta: ${mean_delta:+,.2f}")
    print("=" * 145)

if __name__ == "__main__":
    main()
