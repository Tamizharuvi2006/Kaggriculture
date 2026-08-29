"""EXP150 Multi-Process Mirror Detector Worker."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def profile_match(seed: int, seat: int, b_key: str):
    opp_entry = POPULATION_SUITE[b_key]
    opp_fn = opp_entry["agent"]
    is_mirror = (b_key == "T1_v18_mirror")

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    snapshots = {}
    step_checkpoints = [72, 96, 120, 144, 168, 192, 216, 240]

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        if step in step_checkpoints:
            farms = obs0.get("farms", [{}, {}])
            opp_f = farms[1 - seat] if len(farms) > 1 - seat else {}
            opp_tiles = opp_f.get("tiles", [])
            opp_money = float(opp_f.get("money", 0))
            opp_unlocked = len(opp_f.get("unlocked_quadrants") or [0])

            opp_straw = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_carrots = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "CARROT")
            opp_wheat = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
            opp_cows = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
            opp_sheep = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")

            snapshots[f"step_{step}"] = {
                "opp_money": opp_money,
                "opp_unlocked": opp_unlocked,
                "opp_straw": opp_straw,
                "opp_carrots": opp_carrots,
                "opp_wheat": opp_wheat,
                "opp_cows": opp_cows,
                "opp_sheep": opp_sheep,
            }

        a0 = sub_d1.agent(obs0, env.configuration)
        try:
            a1 = opp_fn(obs1, env.configuration)
        except TypeError:
            a1 = opp_fn(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "bot_key": b_key,
        "is_mirror": is_mirror,
        "seed": seed,
        "seat": seat,
        "hero_reward": r0,
        "opp_reward": r1,
        "won": r0 > r1,
        "snapshots": snapshots,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp150_worker.py <bot_key_csv> <worker_id>")
        return

    bot_keys = sys.argv[1].split(",")
    worker_id = sys.argv[2]

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    results = []
    for b_key in bot_keys:
        if b_key not in POPULATION_SUITE: continue
        for i, seed in enumerate(seeds):
            seat = 0 if i < 10 else 1
            res = profile_match(seed, seat, b_key)
            results.append(res)

    out_file = os.path.join(REPORTS_DIR, f"exp150_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{worker_id}] complete -> {out_file}")

if __name__ == "__main__":
    main()
