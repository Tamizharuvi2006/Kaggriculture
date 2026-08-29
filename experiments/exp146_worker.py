"""EXP146 Multi-Opponent Worker: Evaluates Arms A, B, C, D, E, F across benchmark opponent suites."""
from __future__ import annotations
import os
import sys
import json
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from experiments.exp146_agents import (
    agent_arm_a, agent_arm_b, agent_arm_c, agent_arm_d, agent_arm_e, agent_arm_f
)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_bot(bot_filename: str):
    p = os.path.join(BASE_DIR, "baseline", bot_filename)
    spec = importlib.util.spec_from_file_location("opp_bot", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_match(seed: int, seat: int, ag_fn, bot_mod):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = ag_fn(obs0, env.configuration)
        try:
            a1 = bot_mod.agent(obs1, env.configuration)
        except TypeError:
            a1 = bot_mod.agent(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])
    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return r0, r1, r0 > r1

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp146_worker.py <bot_filename> <worker_id>")
        return

    bot_filename = sys.argv[1]
    worker_id = sys.argv[2]
    bot_mod = load_bot(bot_filename)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    results = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1

        r_a, opp_a, won_a = run_match(seed, seat, agent_arm_a, bot_mod)
        r_b, opp_b, won_b = run_match(seed, seat, agent_arm_b, bot_mod)
        r_c, opp_c, won_c = run_match(seed, seat, agent_arm_c, bot_mod)
        r_d, opp_d, won_d = run_match(seed, seat, agent_arm_d, bot_mod)
        r_e, opp_e, won_e = run_match(seed, seat, agent_arm_e, bot_mod)
        r_f, opp_f, won_f = run_match(seed, seat, agent_arm_f, bot_mod)

        results.append({
            "opponent": bot_filename,
            "seed": seed,
            "seat": seat,
            "arm_a": {"reward": r_a, "opp": opp_a, "won": won_a},
            "arm_b": {"reward": r_b, "opp": opp_b, "won": won_b},
            "arm_c": {"reward": r_c, "opp": opp_c, "won": won_c},
            "arm_d": {"reward": r_d, "opp": opp_d, "won": won_d},
            "arm_e": {"reward": r_e, "opp": opp_e, "won": won_e},
            "arm_f": {"reward": r_f, "opp": opp_f, "won": won_f},
            "delta_b_vs_a": r_b - r_a,
            "delta_c_vs_a": r_c - r_a,
            "delta_d_vs_a": r_d - r_a,
            "delta_e_vs_a": r_e - r_a,
            "delta_f_vs_a": r_f - r_a,
        })

    out_file = os.path.join(REPORTS_DIR, f"exp146_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{bot_filename}:{worker_id}] complete -> {out_file}")

if __name__ == "__main__":
    main()
