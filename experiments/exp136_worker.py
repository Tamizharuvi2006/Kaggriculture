"""EXP136 Chunk Worker: Step-696 Bug-Fix Isolation Benchmark."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def d1_bugfixed_agent(obs, config=None):
    """Arm B: Surgically Bug-Fixed D.1.

    Preserves core schedule's HIREs at Step 696 while prioritizing liquidation sells,
    capped strictly at the 10-order limit.
    """
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    act = sub_d1.agent(obs, config)
    day = (step // 24) + 1
    hour = step % 24

    if day == 30 and hour == 0:
        orders = list(act.get("market") or [])
        slots = max(0, 10 - len(orders))
        for _ in range(slots):
            orders.append(["HIRE"])
        act["market"] = orders[:10]
    return act

def run_match(seed: int, seat: int):
    # Control A (Bugged D.1)
    env_a = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_a.reset()
    while not env_a.done:
        obs0 = env_a.state[0].observation if seat == 0 else env_a.state[1].observation
        obs1 = env_a.state[1].observation if seat == 0 else env_a.state[0].observation
        a0 = sub_d1.agent(obs0, env_a.configuration)
        try:
            a1 = bot_v18_mod.agent(obs1, env_a.configuration)
        except TypeError:
            a1 = bot_v18_mod.agent(obs1)
        env_a.step([a0, a1] if seat == 0 else [a1, a0])
    r_a0 = float(env_a.state[seat].reward or 0.0)
    r_a1 = float(env_a.state[1 - seat].reward or 0.0)
    won_a = r_a0 > r_a1

    # Arm B (Bug-Fixed D.1)
    env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_b.reset()
    while not env_b.done:
        obs0 = env_b.state[0].observation if seat == 0 else env_b.state[1].observation
        obs1 = env_b.state[1].observation if seat == 0 else env_b.state[0].observation
        a0 = d1_bugfixed_agent(obs0, env_b.configuration)
        try:
            a1 = bot_v18_mod.agent(obs1, env_b.configuration)
        except TypeError:
            a1 = bot_v18_mod.agent(obs1)
        env_b.step([a0, a1] if seat == 0 else [a1, a0])
    r_b0 = float(env_b.state[seat].reward or 0.0)
    r_b1 = float(env_b.state[1 - seat].reward or 0.0)
    won_b = r_b0 > r_b1

    return {
        "seed": seed,
        "seat": seat,
        "ctrl_rew": r_a0,
        "ctrl_opp": r_a1,
        "ctrl_won": won_a,
        "fix_rew": r_b0,
        "fix_opp": r_b1,
        "fix_won": won_b,
        "delta": r_b0 - r_a0,
    }

def main():
    if len(sys.argv) < 4:
        print("Usage: python exp136_worker.py <cohort_type> <start_idx> <end_idx>")
        return

    cohort_type = sys.argv[1]  # "loss" or "fresh"
    start_idx = int(sys.argv[2])
    end_idx = int(sys.argv[3])

    if cohort_type == "loss":
        loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
        with open(loss_file, "r", encoding="utf-8") as f:
            cohort_data = json.load(f)
        chunk = cohort_data[start_idx:end_idx]
        matches = [(m["seed"], m["seat"]) for m in chunk]
    else:
        fresh_seeds = list(range(20001, 20101))
        chunk = fresh_seeds[start_idx:end_idx]
        matches = [(seed, 0) for seed in chunk]

    results = []
    for i, (seed, seat) in enumerate(matches, start=start_idx + 1):
        res = run_match(seed, seat)
        res["match_id"] = i
        res["cohort_type"] = cohort_type
        results.append(res)

    out_part = os.path.join(REPORTS_DIR, f"exp136_{cohort_type}_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{cohort_type}:{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
