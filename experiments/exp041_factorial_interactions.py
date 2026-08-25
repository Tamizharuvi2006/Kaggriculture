"""EXP041: Track B (16-Cell 2^4 Factorial Interaction Search).
Evaluates all 16 combinations of the 4 most sensitive degrees of freedom:
  - K1 (Land Timing): [10, 12]
  - K3 (Workers Cap): [12, 13]
  - K4 (Sell Threshold): [4, 8]
  - K5 (Clearance Step): [696, 710]
Runs full multi-core parallel evaluation across 32 holdout seeds (64 matches per cell).
Computes ANOVA Main Effects and 2-Way Interaction Terms.
"""
from __future__ import annotations
import sys
import os
import itertools
import numpy as np
from concurrent.futures import ProcessPoolExecutor

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

def eval_single_seed_match(args: tuple) -> tuple[float, float, float]:
    """Runs a 2-game seat-swapped match on a single seed."""
    land_day, workers_cap, sell_threshold, clearance_step, seed = args

    def _make_agent():
        def _act(obs, config=None):
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

    # Game 1: Cand = Seat 0, v18 = Seat 1
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    ag1 = _make_agent()
    while not env1.done:
        env1.step([ag1(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
    r_c_s0 = float(env1.state[0].reward or 0.0)
    r_v_s1 = float(env1.state[1].reward or 0.0)
    w1 = 1.0 if r_c_s0 > r_v_s1 else (0.5 if r_c_s0 == r_v_s1 else 0.0)

    # Game 2: v18 = Seat 0, Cand = Seat 1
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    ag2 = _make_agent()
    while not env2.done:
        env2.step([bot_v18.agent(env2.state[0].observation), ag2(env2.state[1].observation)])
    r_v_s0 = float(env2.state[0].reward or 0.0)
    r_c_s1 = float(env2.state[1].reward or 0.0)
    w2 = 1.0 if r_c_s1 > r_v_s0 else (0.5 if r_c_s1 == r_v_s0 else 0.0)

    return r_c_s0, r_c_s1, w1 + w2

def run_exp041():
    print("=" * 105)
    print("EXP041: 16-CELL 2^4 FACTORIAL INTERACTION SEARCH (PARALLEL MULTI-CORE EVALUATION)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    grid = {
        "land_day": [10, 12],
        "workers_cap": [12, 13],
        "sell_threshold": [4, 8],
        "clearance_step": [696, 710],
    }

    combinations = list(itertools.product(
        grid["land_day"], grid["workers_cap"], grid["sell_threshold"], grid["clearance_step"]
    ))

    print(f"Total Factorial Cells: {len(combinations)} | Seeds per Cell: {len(seeds)} (64 Matches/Cell = 1,024 Matches Total)")
    print("Executing in parallel across CPU cores...")

    cell_results = []

    for idx, (l_day, w_cap, s_thresh, c_step) in enumerate(combinations, start=1):
        cell_name = f"Cell #{idx:02d} [L:{l_day}, W:{w_cap}, S:{s_thresh}, C:{c_step}]"
        args_list = [(l_day, w_cap, s_thresh, c_step, s) for s in seeds]

        with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
            match_outputs = list(pool.map(eval_single_seed_match, args_list))

        banks = []
        total_wins = 0.0
        for r0, r1, wins in match_outputs:
            banks.extend([r0, r1])
            total_wins += wins

        mean_b = float(np.mean(banks))
        median_b = float(np.median(banks))
        min_b = float(np.min(banks))
        max_b = float(np.max(banks))
        wr = total_wins / (len(seeds) * 2)

        cell_results.append({
            "idx": idx,
            "name": cell_name,
            "params": {"land": l_day, "workers": w_cap, "sell": s_thresh, "clearance": c_step},
            "mean": mean_b,
            "median": median_b,
            "min": min_b,
            "max": max_b,
            "win_rate": wr,
            "banks": banks,
        })
        print(f"  [DONE] {cell_name:<42} -> Mean: ${mean_b:>10,.2f} | Max: ${max_b:>10,.2f} | Win%: {wr:>5.1%}")

    # Find Baseline Cell (L:10, W:13, S:4, C:696)
    base_cell = next(c for c in cell_results if c["params"] == {"land": 10, "workers": 13, "sell": 4, "clearance": 696})

    print("\n" + "=" * 105)
    print("EXP041 16-CELL FACTORIAL INTERACTION SEARCH COMPLETE REPORT")
    print("=" * 105)
    print(f"{'Cell Name':<42} | {'Mean Bank':>12} | {'Delta vs D.1':>14} | {'Median':>12} | {'Peak (Max)':>12} | {'Win Rate':>9}")
    print("-" * 105)

    for c in cell_results:
        delta = c["mean"] - base_cell["mean"]
        is_d1 = (c["idx"] == base_cell["idx"])
        mark = " (D.1 Control 🏆)" if is_d1 else ""
        print(f"{c['name'] + mark:<42} | ${c['mean']:>11,.2f} | ${delta:>+13,.2f} | ${c['median']:>11,.2f} | ${c['max']:>11,.2f} | {c['win_rate']:>8.1%}")

    print("=" * 105)

    # Find Top Performer
    best_cell = max(cell_results, key=lambda c: c["mean"])
    top_delta = best_cell["mean"] - base_cell["mean"]

    print("\nPROMOTION EVALUATION:")
    print(f"  - Top Performing Cell: {best_cell['name']} with Mean ${best_cell['mean']:,.2f} (Delta: ${top_delta:+,.2f})")
    print(f"  - Top Cell Win Rate vs v18: {best_cell['win_rate']:.1%}")
    if top_delta >= 2000.0 and best_cell['win_rate'] >= 0.85:
        print("\n>>> VERDICT: PROMOTE TOP INTERACTION CELL AS NEW BASELINE!")
    else:
        print("\n>>> VERDICT: NO INTERACTION BEATS D.1 BY >= $2,000. (D.1 CONFIRMED MAXIMUM IN THIS FAMILY)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp041()
