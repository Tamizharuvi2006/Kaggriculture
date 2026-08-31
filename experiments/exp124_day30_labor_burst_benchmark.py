"""EXP124: Fast Parallelized Day-30 Emergency Labor Burst Benchmark (100 Matches).

Optimized for 12-core parallel execution (10 worker processes).
Evaluates Arm A (Control D.1) vs Arm B (Day 30 Labor Burst) on the 100 frozen D.1 loss seeds.
"""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Module-level agent holder for worker processes
_SUB_D1 = None
_BOT_V18 = None

def _init_worker(base_dir: str):
    global _SUB_D1, _BOT_V18
    spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(base_dir, "submission_clean.py"))
    _SUB_D1 = importlib.util.module_from_spec(spec_d1)
    spec_d1.loader.exec_module(_SUB_D1)

    spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(base_dir, "baseline", "kaitofukami-v18.py"))
    _BOT_V18 = importlib.util.module_from_spec(spec_v18)
    spec_v18.loader.exec_module(_BOT_V18)

class Day30LaborBurstAgent:
    def __init__(self, enable_burst: bool = False, max_hires: int = 6):
        self.enable_burst = enable_burst
        self.max_hires = max_hires

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = _SUB_D1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Day 30 Hour 0: Inject emergency labor hires
        if self.enable_burst and day == 30 and hour == 0:
            slots_available = max(0, 10 - len(market_orders))
            hires_to_add = min(self.max_hires, slots_available)
            for _ in range(hires_to_add):
                market_orders.append(["HIRE"])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def _run_single_match(agent_d1_obj, seed: int, d1_seat: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    seat_0_is_d1 = (d1_seat == 0)

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        # D1 Action
        d1_obs = obs0 if seat_0_is_d1 else obs1
        a_d1 = agent_d1_obj.act(d1_obs, env.configuration)

        # Opponent Action
        opp_obs = obs1 if seat_0_is_d1 else obs0
        try:
            a_opp = _BOT_V18.agent(opp_obs, env.configuration)
        except TypeError:
            a_opp = _BOT_V18.agent(opp_obs) if hasattr(_BOT_V18, "agent") else _BOT_V18(opp_obs)

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    d1_rew = r0 if seat_0_is_d1 else r1
    opp_rew = r1 if seat_0_is_d1 else r0
    won = d1_rew > opp_rew
    delta = d1_rew - opp_rew

    # Count stranded crops
    final_obs = env.state[d1_seat].observation
    farms = final_obs.get("farms", [])
    d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
    stranded = 0
    for row in (d1_farm.get("tiles") or []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("kind") == "PLANT":
                if tile.get("yield_units", 0) > 0:
                    stranded += 1

    return {
        "reward": d1_rew,
        "opp_reward": opp_rew,
        "won": won,
        "delta": delta,
        "stranded": stranded,
    }

def _eval_pair_worker(task_tuple):
    idx, seed, seat = task_tuple
    agent_a = Day30LaborBurstAgent(enable_burst=False)
    res_a = _run_single_match(agent_a, seed=seed, d1_seat=seat)

    agent_b = Day30LaborBurstAgent(enable_burst=True, max_hires=6)
    res_b = _run_single_match(agent_b, seed=seed, d1_seat=seat)

    reward_delta = res_b["reward"] - res_a["reward"]

    if not res_a["won"] and res_b["won"]:
        transition = "LOSS_TO_WIN"
    elif not res_a["won"] and not res_b["won"]:
        transition = "LOSS_TO_LOSS"
    elif res_a["won"] and not res_b["won"]:
        transition = "WIN_TO_LOSS"
    else:
        transition = "WIN_TO_WIN"

    return {
        "match_id": idx,
        "seed": seed,
        "seat": seat,
        "arm_a_reward": res_a["reward"],
        "arm_a_opp_reward": res_a["opp_reward"],
        "arm_a_won": res_a["won"],
        "arm_a_stranded": res_a["stranded"],
        "arm_b_reward": res_b["reward"],
        "arm_b_opp_reward": res_b["opp_reward"],
        "arm_b_won": res_b["won"],
        "arm_b_stranded": res_b["stranded"],
        "reward_delta": reward_delta,
        "transition": transition,
        "stranded_reduced": res_a["stranded"] - res_b["stranded"],
    }

def main():
    print("=" * 135)
    print("EXP124: PARALLELIZED DAY-30 LABOR BURST BENCHMARK (100 MATCHES ON 10 CORES)")
    print("=" * 135)

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    tasks = [(i, m["seed"], m["seat"]) for i, m in enumerate(loss_cohort, 1)]
    print(f"Dispatched {len(tasks)} parallel evaluation tasks across 10 worker processes...")

    workers_count = min(10, os.cpu_count() or 4)
    with Pool(processes=workers_count, initializer=_init_worker, initargs=(BASE_DIR,)) as pool:
        comparison_results = pool.map(_eval_pair_worker, tasks)

    df_comp = pd.DataFrame(comparison_results)

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP124: STATISTICAL SYNTHESIS & WIN-CONVERSION RESULTS (100 MATCHES)")
    print("=" * 135)

    loss_to_win = (df_comp["transition"] == "LOSS_TO_WIN").sum()
    loss_to_loss = (df_comp["transition"] == "LOSS_TO_LOSS").sum()
    win_to_loss = (df_comp["transition"] == "WIN_TO_LOSS").sum()
    win_to_win = (df_comp["transition"] == "WIN_TO_WIN").sum()
    net_conversion = loss_to_win - win_to_loss

    print("\n1. MATCH OUTCOME TRANSITION MATRIX:")
    print(f"   - Loss -> Win Conversions  (✅ SUCCESS)   : {loss_to_win:2d} matches ({loss_to_win:4.1f}%)")
    print(f"   - Loss -> Loss Unconverted (❌ NEUTRAL)   : {loss_to_loss:2d} matches ({loss_to_loss:4.1f}%)")
    print(f"   - Win -> Loss Regressions  (🚨 DANGER)    : {win_to_loss:2d} matches ({win_to_loss:4.1f}%)")
    print(f"   - Win -> Win Preserved     (✅ STABLE)    : {win_to_win:2d} matches ({win_to_win:4.1f}%)")
    print(f"   -----------------------------------------------------------------")
    print(f"   - NET CONVERSION SCORE     : {net_conversion:+d} matches ({net_conversion:+4.1f}%)")

    deltas = df_comp["reward_delta"]
    print(f"\n2. TERMINAL REWARD DELTA DISTRIBUTION (Arm B vs Arm A):")
    print(f"   - Mean Reward Delta   : ${deltas.mean():+10,.2f}")
    print(f"   - Median Reward Delta : ${deltas.median():+10,.2f}")
    print(f"   - Min Reward Delta    : ${deltas.min():+10,.2f}")
    print(f"   - Max Reward Delta    : ${deltas.max():+10,.2f}")
    print(f"   - Positive Delta Ratio: {(deltas > 0).sum():2d}/100 matches ({(deltas > 0).mean()*100:4.1f}%)")

    stranded_a = df_comp["arm_a_stranded"].mean()
    stranded_b = df_comp["arm_b_stranded"].mean()
    print(f"\n3. FIELD CLEARING & HARVEST EFFICIENCY:")
    print(f"   - Mean Stranded Crops in Arm A (Control) : {stranded_a:.2f} plots")
    print(f"   - Mean Stranded Crops in Arm B (Burst)   : {stranded_b:.2f} plots (Reduced by {stranded_a - stranded_b:.2f} plots)")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp124_day30_labor_burst_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2)
    print(f"\nSaved Full EXP124 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
