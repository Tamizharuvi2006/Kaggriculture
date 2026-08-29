"""EXP152 Multi-Process Worker: Evaluating Arms A, B, C across the 10-archetype population suite."""
from __future__ import annotations
import os
import sys
import json
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE
from experiments.test_exp152_proof import (
    agent_arm_a, agent_arm_b_hire_first, agent_arm_c_liq_first
)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def run_match(seed: int, seat: int, hero_fn, opp_fn):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = hero_fn(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])
    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return r0, r1, r0 > r1

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp152_worker.py <bot_key_csv> <worker_id>")
        return

    bot_keys = sys.argv[1].split(",")
    worker_id = sys.argv[2]

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    results = []
    for b_key in bot_keys:
        if b_key not in POPULATION_SUITE: continue
        opp_entry = POPULATION_SUITE[b_key]
        opp_fn = opp_entry["agent"]
        tier = opp_entry["tier"]
        archetype = opp_entry["archetype"]

        for i, seed in enumerate(seeds):
            seat = 0 if i < 10 else 1

            r_a, opp_a, won_a = run_match(seed, seat, agent_arm_a, opp_fn)
            r_b, opp_b, won_b = run_match(seed, seat, agent_arm_b_hire_first, opp_fn)
            r_c, opp_c, won_c = run_match(seed, seat, agent_arm_c_liq_first, opp_fn)

            results.append({
                "bot_key": b_key,
                "tier": tier,
                "archetype": archetype,
                "seed": seed,
                "seat": seat,
                "arm_a": {"reward": r_a, "opp": opp_a, "won": won_a},
                "arm_b": {"reward": r_b, "opp": opp_b, "won": won_b},
                "arm_c": {"reward": r_c, "opp": opp_c, "won": won_c},
                "delta_b_vs_a": r_b - r_a,
                "delta_c_vs_a": r_c - r_a,
            })

    out_file = os.path.join(REPORTS_DIR, f"exp152_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{worker_id}] completed {len(results)} match triples -> {out_file}")

if __name__ == "__main__":
    main()
