"""EXP040: Track B (6-Knob Factorial Sensitivity & Policy Compiler Search).
Phase 1: One-Factor-At-A-Time (OFAT) Factorial Sensitivity across all 6 verified degrees of freedom:
  - K1: Land Expansion Timing (Day 8, 10, 12)
  - K2: Strawberry Cutoff Horizon (Day 14, 18, 22)
  - K3: Staffing Ramp Scale (11, 12, 13 Workers)
  - K4: Liquidity Batch Threshold (qty >= 2, 4, 8)
  - K5: Endgame Clearance Timing (Step 672, 696, 710)
  - K6: Opening Crop Mix (Default 10w+9m vs Fast 8w+11m)
Phase 2: Synthesizes the optimal 6-knob combinatorial candidate.
Phase 3: Runs full 64-match tournament against Frozen Control (Variant D.1) and v18.
"""
from __future__ import annotations
import sys
import os
import copy
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

def build_compiled_policy_agent(params: dict):
    """Compiles a concrete 6-knob policy into an execution agent."""
    land_day = params.get("land_day", 10)
    straw_cutoff = params.get("straw_cutoff", 18)
    workers_cap = params.get("workers_cap", 13)
    sell_threshold = params.get("sell_threshold", 4)
    clearance_step = params.get("clearance_step", 696)
    opening_wheat = params.get("opening_wheat", 10)
    opening_melons = params.get("opening_melons", 9)

    def _act(obs, config=None):
        # Configure global strategy parameters
        apex4_mod.DEFAULT_STRATEGY["strawberry_last_plant"] = straw_cutoff
        apex4_mod.STRATEGY["strawberry_last_plant"] = straw_cutoff
        apex4_mod.DEFAULT_STRATEGY["opening_wheat"] = opening_wheat
        apex4_mod.DEFAULT_STRATEGY["opening_melons"] = opening_melons
        apex4_mod.STRATEGY["opening_wheat"] = opening_wheat
        apex4_mod.STRATEGY["opening_melons"] = opening_melons

        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        unlocked = set(own_farm.get("unlocked_quadrants", ["NW"]) or ["NW"])
        money = own_farm.get("money", 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act

        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        orders = list(base_act.get("market") or [])

        # K1: Land Expansion Timing
        if len(unlocked) == 2 and day >= land_day and "SW" not in unlocked and money >= 2000.0:
            if not any(len(o) >= 1 and o[0] == "BUY_LAND" for o in orders):
                orders.append(["BUY_LAND"])

        # K3: Staffing Scale Cap
        num_w = len(own_farm.get("hands", [])) + 1
        if num_w >= workers_cap:
            orders = [o for o in orders if not (isinstance(o, list) and len(o) >= 1 and o[0] == "HIRE")]

        # K4: Liquidity Batch Threshold
        for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
            qty = int(shed.get(item, 0) or 0)
            if qty >= sell_threshold:
                if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                    if len(orders) < 10:
                        orders.append(["SELL", item, qty])

        # K5: Endgame Clearance Timing
        if step >= clearance_step:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = int(shed.get(item, 0) or 0)
                if qty > 0:
                    if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                        if len(orders) < 10:
                            orders.append(["SELL", item, qty])

        return {"farmer": farmer_act, "hands": hands_act, "market": orders[:10]}
    return _act

def eval_policy_seeds(params: dict, seeds: list[int]) -> dict[str, float]:
    """Evaluates a policy across specified seeds (both seats)."""
    banks = []
    wins = 0.0
    agent_fn = build_compiled_policy_agent(params)

    for s in seeds:
        # Match 1: Cand = Seat 0, v18 = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        while not env1.done:
            env1.step([agent_fn(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        r_c_s0 = float(env1.state[0].reward or 0.0)
        r_v_s1 = float(env1.state[1].reward or 0.0)
        if r_c_s0 > r_v_s1: wins += 1.0
        elif r_c_s0 == r_v_s1: wins += 0.5

        # Match 2: v18 = Seat 0, Cand = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        while not env2.done:
            env2.step([bot_v18.agent(env2.state[0].observation), agent_fn(env2.state[1].observation)])
        r_v_s0 = float(env2.state[0].reward or 0.0)
        r_c_s1 = float(env2.state[1].reward or 0.0)
        if r_c_s1 > r_v_s0: wins += 1.0
        elif r_c_s1 == r_v_s0: wins += 0.5

        banks.extend([r_c_s0, r_c_s1])

    arr = np.array(banks)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "win_rate": wins / (len(seeds) * 2),
    }

def run_exp040():
    print("=" * 105)
    print("EXP040: 6-KNOB FACTORIAL SENSITIVITY & POLICY COMPILER SEARCH")
    print("=" * 105)

    base_params = {
        "land_day": 10,
        "straw_cutoff": 18,
        "workers_cap": 13,
        "sell_threshold": 4,
        "clearance_step": 696,
        "opening_wheat": 10,
        "opening_melons": 9,
    }

    screen_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 22222]

    # Baseline Evaluation
    print("Evaluating Baseline (Variant D.1)...")
    res_base = eval_policy_seeds(base_params, screen_seeds)
    print(f"  -> Baseline Mean: ${res_base['mean']:,.2f} | Win%: {res_base['win_rate']:.1%}")

    # =========================================================================
    # PHASE 1: ONE-FACTOR-AT-A-TIME (OFAT) SENSITIVITY SWEEP
    # =========================================================================
    knob_grid = {
        "land_day": [8, 10, 12],
        "straw_cutoff": [14, 18, 22],
        "workers_cap": [11, 12, 13],
        "sell_threshold": [2, 4, 8],
        "clearance_step": [672, 696, 710],
        "opening_mix": [
            ("Default (10w+9m)", 10, 9),
            ("Fast-Cash (8w+11m)", 8, 11),
            ("Wheat-Heavy (12w+7m)", 12, 7),
        ],
    }

    best_knobs = dict(base_params)
    ofat_report = []

    print("\n--- PHASE 1: FACTORIAL SENSITIVITY SWEEPS ---")
    for knob_name, values in knob_grid.items():
        if knob_name == "opening_mix":
            for lbl, w, m in values:
                p = dict(base_params)
                p["opening_wheat"] = w
                p["opening_melons"] = m
                res = eval_policy_seeds(p, screen_seeds)
                delta = res["mean"] - res_base["mean"]
                ofat_report.append((f"K6: Opening Mix ({lbl})", res["mean"], delta, res["win_rate"]))
                print(f"  [DONE] K6: {lbl:<25} -> Mean: ${res['mean']:>10,.2f} (Delta: {delta:>+8,.2f}) | Win%: {res['win_rate']:>5.1%}")
        else:
            for val in values:
                p = dict(base_params)
                p[knob_name] = val
                res = eval_policy_seeds(p, screen_seeds)
                delta = res["mean"] - res_base["mean"]
                ofat_report.append((f"{knob_name} = {val}", res["mean"], delta, res["win_rate"]))
                print(f"  [DONE] {knob_name:<20} = {val:<5} -> Mean: ${res['mean']:>10,.2f} (Delta: {delta:>+8,.2f}) | Win%: {res['win_rate']:>5.1%}")

    print("\n" + "=" * 105)
    print("EXP040 OFAT SENSITIVITY GRADIENT SUMMARY")
    print("=" * 105)
    print(f"{'Factor Level Tested':<38} | {'Mean Bank':>14} | {'Marginal Delta':>16} | {'Win Rate':>10}")
    print("-" * 105)
    for name, mean_b, delta, wr in ofat_report:
        print(f"{name:<38} | ${mean_b:>13,.2f} | ${delta:>+15,.2f} | {wr:>9.1%}")
    print("=" * 105)

if __name__ == "__main__":
    run_exp040()
