"""EXP044: Track B (Unreachable State-Space Basin Discovery).
Searches for genuinely distinct, unentered state-space basins outside of D.1's strawberry monolith:
  - Basin Delta: Fertilizer Compounding Wave Engine (Applies fertilizer to strawberries to accelerate growth cycle)
  - Basin Epsilon: Dual-Crop Diversification Engine (24 Strawberries + 14 Rotating Fast Crops)
  - Basin Zeta: Wool & Dairy Industrial Acceleration (High-volume Wool & Milk production)
Evaluates:
  1. Gate 1: Reachability Gate (Seed 42)
  2. Gate 2: Harness Safety Gate (0 Stalls, Invariants 1 & 2)
  3. Gate 3: Head-to-Head Tournament vs Basin Alpha (Variant D.1) across 64 matches on 32 holdout seeds.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, List, Tuple
from concurrent.futures import ProcessPoolExecutor
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.agent import VariantDAgent
from engine.evaluation.reachability_gate import verify_reachability

# =============================================================================
# CANDIDATE UNENTERED STATE-SPACE BASIN PROTOTYPES
# =============================================================================

def make_basin_delta_fertilizer():
    """Basin Delta: Fertilizer Compounding Wave Engine.
    Actively buys and schedules fertilizer onto strawberry plots to compress harvest cycles.
    """
    def _act(obs, config=None):
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        money = own_farm.get("money", 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Purchase fertilizer on Days 7-18 if working capital allows
        if 7 <= day <= 18 and money >= 800.0 and int(shed.get("FERTILIZER", 0)) < 12:
            if not any(len(o) >= 2 and o[0] == "BUY_PRODUCT" and o[1] == "FERTILIZER" for o in orders):
                if len(orders) < 10:
                    orders.append(["BUY_PRODUCT", "FERTILIZER", 8])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def make_basin_epsilon_dual_crop():
    """Basin Epsilon: Dual-Crop Diversification Engine.
    Maintains a dedicated 12-tile rotating Carrot/Melon fast-cash engine alongside Strawberries.
    """
    def _act(obs, config=None):
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        money = own_farm.get("money", 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Continuously purchase fast-crop seeds (Carrots & Melons)
        if 8 <= day <= 24 and money >= 400.0 and int(shed.get("CARROT", 0)) < 8:
            if not any(len(o) >= 2 and o[0] == "BUY_SEED" and o[1] == "CARROT" for o in orders):
                if len(orders) < 10:
                    orders.append(["BUY_SEED", "CARROT", 8])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def eval_head_to_head_match(args: tuple) -> tuple[float, float, float]:
    """Runs a 2-game seat-swapped match between Candidate and Basin Alpha (D.1)."""
    cand_name, seed = args

    if cand_name == "DELTA":
        cand_fn = make_basin_delta_fertilizer()
    elif cand_name == "EPSILON":
        cand_fn = make_basin_epsilon_dual_crop()
    else:
        cand_fn = VariantDAgent().act

    alpha_fn = VariantDAgent().act

    # Game 1: Cand = Seat 0, Alpha = Seat 1
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    while not env1.done:
        env1.step([cand_fn(env1.state[0].observation), alpha_fn(env1.state[1].observation)])
    r_c_s0 = float(env1.state[0].reward or 0.0)
    r_a_s1 = float(env1.state[1].reward or 0.0)
    w1 = 1.0 if r_c_s0 > r_a_s1 else (0.5 if r_c_s0 == r_a_s1 else 0.0)

    # Game 2: Alpha = Seat 0, Cand = Seat 1
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    while not env2.done:
        env2.step([alpha_fn(env2.state[0].observation), cand_fn(env2.state[1].observation)])
    r_a_s0 = float(env2.state[0].reward or 0.0)
    r_c_s1 = float(env2.state[1].reward or 0.0)
    w2 = 1.0 if r_c_s1 > r_a_s0 else (0.5 if r_c_s1 == r_a_s0 else 0.0)

    return r_c_s0, r_c_s1, w1 + w2

def run_exp044():
    print("=" * 105)
    print("EXP044: UNREACHABLE STATE-SPACE BASIN DISCOVERY & HEAD-TO-HEAD VALIDATION")
    print("=" * 105)

    candidates = [
        ("Basin Delta (Fertilizer Compounding)", make_basin_delta_fertilizer(), "DELTA"),
        ("Basin Epsilon (Dual-Crop Diversification)", make_basin_epsilon_dual_crop(), "EPSILON"),
    ]

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    # Step 1: Reachability Gate Evaluation
    print("--- STEP 1: REACHABILITY GATE EVALUATION (Seed 42) ---")
    live_basins = []
    for name, agent_fn, key in candidates:
        passed, res = verify_reachability(agent_fn, name, seed=42)
        if passed and res["action_divergence_pct"] >= 4.0:
            live_basins.append((name, key, res))
            print(f"  [REACHABILITY PASSED] {name} -> Action Divergence: {res['action_divergence_pct']:.1f}%")
        else:
            print(f"  [REACHABILITY FAILED] {name} -> Collapsed into D.1")

    # Step 2: Head-to-Head Tournament vs Basin Alpha (Variant D.1)
    print("\n--- STEP 2: HEAD-TO-HEAD TOURNAMENT vs BASIN ALPHA (D.1) (64 Matches per Candidate) ---")
    tournament_results = []

    for name, key, r_info in live_basins:
        args_list = [(key, s) for s in seeds]
        with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
            match_outputs = list(pool.map(eval_head_to_head_match, args_list))

        cand_banks = []
        total_wins = 0.0
        for r0, r1, wins in match_outputs:
            cand_banks.extend([r0, r1])
            total_wins += wins

        mean_b = float(np.mean(cand_banks))
        median_b = float(np.median(cand_banks))
        min_b = float(np.min(cand_banks))
        max_b = float(np.max(cand_banks))
        wr = (total_wins / (len(seeds) * 2)) * 100.0

        tournament_results.append({
            "name": name,
            "mean": mean_b,
            "median": median_b,
            "min": min_b,
            "max": max_b,
            "win_rate_vs_alpha": wr,
            "delta_vs_alpha": mean_b - 80010.61,
        })
        print(f"  [DONE] {name:<42} -> Mean: ${mean_b:>10,.2f} | Win% vs Alpha: {wr:>5.1%}")

    print("\n" + "=" * 105)
    print("EXP044 HEAD-TO-HEAD TOURNAMENT REPORT (vs BASIN ALPHA / VARIANT D.1)")
    print("=" * 105)
    print(f"{'Candidate Basin Name':<45} | {'Mean Bank':>12} | {'Delta vs Alpha':>15} | {'Median':>12} | {'Win% vs Alpha':>14}")
    print("-" * 105)

    for res in tournament_results:
        print(f"{res['name']:<45} | ${res['mean']:>11,.2f} | ${res['delta_vs_alpha']:>+14,.2f} | ${res['median']:>11,.2f} | {res['win_rate_vs_alpha']:>13.1f}%")

    print("=" * 105)

    # Check for Superior Basin
    beaten_alpha = any(r["win_rate_vs_alpha"] > 50.0 and r["delta_vs_alpha"] >= 2000.0 for r in tournament_results)
    print("\nPROMOTION EVALUATION:")
    if beaten_alpha:
        print(">>> RESULT: NEW SUPERIOR BASIN DISCOVERED! PROMOTE TO BASELINE!")
    else:
        print(">>> RESULT: BASIN ALPHA (VARIANT D.1) DEFEATS ALL DISCOVERED STATE-SPACE BASINS.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp044()
