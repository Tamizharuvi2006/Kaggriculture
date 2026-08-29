"""EXP150: Saturated Mirror-Regime Detector Mining across the 10-Archetype Population Basket."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

def profile_match_trajectory(seed: int, seat: int, b_key: str):
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

        # Capture public state of opponent (as visible from hero perspective)
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

            # Check market prices
            market = obs0.get("market", {})
            prices = market.get("prices", {})
            p_straw = float(prices.get("STRAWBERRY", 120.0))
            p_milk = float(prices.get("MILK", 120.0))

            snapshots[f"step_{step}"] = {
                "opp_money": opp_money,
                "opp_unlocked": opp_unlocked,
                "opp_straw": opp_straw,
                "opp_carrots": opp_carrots,
                "opp_wheat": opp_wheat,
                "opp_cows": opp_cows,
                "opp_sheep": opp_sheep,
                "p_straw": p_straw,
                "p_milk": p_milk,
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
    print("=" * 145)
    print("EXP150: SATURATED MIRROR-REGIME DETECTOR MINING (ACROSS 10 ARCHETYPES / 200 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    all_matches = []
    print("Collecting step-by-step observable trajectory profiles across all 200 matches...")

    for b_key in all_keys:
        for i, seed in enumerate(seeds):
            seat = 0 if i < 10 else 1
            res = profile_match_trajectory(seed, seat, b_key)
            all_matches.append(res)

    print(f"Profiling complete. Audited {len(all_matches)} matches ({sum(1 for m in all_matches if m['is_mirror'])} mirror matches).\n")

    # 1. Compare Observable Trajectories: Mirror vs Non-Mirror Archetypes
    print("=" * 145)
    print("1. PUBLIC OBSERVABLE SIGNATURE COMPARISON (MIRROR VS NON-MIRROR ARCHETYPES):")
    print("=" * 145)
    print(f"{'Checkpoint Step':<18} | {'Mirror Straw':<15} | {'Non-Mirror Straw':<18} | {'Mirror Cows':<15} | {'Non-Mirror Cows':<18} | {'Mirror Carrots':<15} | {'Non-Mirror Carrots'}")
    print("-" * 145)

    checkpoints = [72, 96, 120, 144, 168, 192, 216, 240]
    mirror_matches = [m for m in all_matches if m["is_mirror"]]
    non_mirror_matches = [m for m in all_matches if not m["is_mirror"]]

    for step in checkpoints:
        k = f"step_{step}"
        m_straw = np.mean([m["snapshots"][k]["opp_straw"] for m in mirror_matches])
        nm_straw = np.mean([m["snapshots"][k]["opp_straw"] for m in non_mirror_matches])
        m_cows = np.mean([m["snapshots"][k]["opp_cows"] for m in mirror_matches])
        nm_cows = np.mean([m["snapshots"][k]["opp_cows"] for m in non_mirror_matches])
        m_carrots = np.mean([m["snapshots"][k]["opp_carrots"] for m in mirror_matches])
        nm_carrots = np.mean([m["snapshots"][k]["opp_carrots"] for m in non_mirror_matches])

        print(f"Step {step:<3} (Day {step//24:02d}){'':<4} | {m_straw:5.2f} tiles{'':<5} | {nm_straw:5.2f} tiles{'':<8} | {m_cows:5.2f} cows{'':<6} | {nm_cows:5.2f} cows{'':<9} | {m_carrots:5.2f} tiles{'':<5} | {nm_carrots:5.2f} tiles")

    # 2. Evaluate Candidate Detectors
    print("\n" + "=" * 145)
    print("2. CANDIDATE DETECTOR ACCURACY MATRIX (PRECISION, RECALL, FALSE POSITIVE RATE):")
    print("=" * 145)
    print(f"{'Detector Rule':<55} | {'Earliest Step':<15} | {'True Positives':<16} | {'False Positives':<16} | {'Accuracy':<10} | {'FPR'}")
    print("-" * 145)

    candidate_rules = [
        # Candidate 1: Day 3/Step 72 (Straw >= 1 and Carrots == 0 and Cows == 0)
        ("Step 72: Straw >= 1 and Carrots == 0", 72,
         lambda snap: snap["step_72"]["opp_straw"] >= 1 and snap["step_72"]["opp_carrots"] == 0),

        # Candidate 2: Day 5/Step 120 (Straw >= 4 and Carrots == 0 and Sheep == 0)
        ("Step 120: Straw >= 4 and Carrots == 0 and Sheep == 0", 120,
         lambda snap: snap["step_120"]["opp_straw"] >= 4 and snap["step_120"]["opp_carrots"] == 0 and snap["step_120"]["opp_sheep"] == 0),

        # Candidate 3: Day 7/Step 168 (Straw >= 6 and Carrots == 0 and Cows <= 5 and Sheep == 0)
        ("Step 168: Straw >= 6 and Carrots == 0 and Cows <= 5", 168,
         lambda snap: snap["step_168"]["opp_straw"] >= 6 and snap["step_168"]["opp_carrots"] == 0 and snap["step_168"]["opp_cows"] <= 5 and snap["step_168"]["opp_sheep"] == 0),

        # Candidate 4: Day 9/Step 216 (Straw >= 14 and Carrots == 0 and Cows in [4..8])
        ("Step 216: Straw >= 14 and Carrots == 0 and Cows <= 8", 216,
         lambda snap: snap["step_216"]["opp_straw"] >= 14 and snap["step_216"]["opp_carrots"] == 0 and snap["step_216"]["opp_cows"] <= 8 and snap["step_216"]["opp_sheep"] == 0),
    ]

    detector_results = []
    for desc, step_trig, fn in candidate_rules:
        tp = sum(1 for m in mirror_matches if fn(m["snapshots"]))
        fn_count = len(mirror_matches) - tp
        fp = sum(1 for m in non_mirror_matches if fn(m["snapshots"]))
        tn = len(non_mirror_matches) - fp

        accuracy = (tp + tn) / len(all_matches) * 100
        fpr = (fp / len(non_mirror_matches)) * 100
        tpr = (tp / len(mirror_matches)) * 100

        detector_results.append({
            "description": desc,
            "step": step_trig,
            "tp": tp, "fp": fp, "fn": fn_count, "tn": tn,
            "accuracy": accuracy, "fpr": fpr, "tpr": tpr,
        })

        print(f"{desc:<55} | Step {step_trig:<9} | {tp}/{len(mirror_matches)} ({tpr:5.1f}%){'':<4} | {fp}/{len(non_mirror_matches)} ({fpr:5.1f}%){'':<4} | {accuracy:5.1f}%    | {fpr:5.1f}%")

    out_json = os.path.join(REPORTS_DIR, "exp150_mirror_detector_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_matches": len(all_matches),
            "mirror_matches": len(mirror_matches),
            "non_mirror_matches": len(non_mirror_matches),
            "detector_candidates": _to_native(detector_results),
            "all_matches": _to_native(all_matches),
        }, f, indent=2)

    print(f"\nSaved Complete EXP150 Detector Mining Results: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
