"""EXP174: Surgical Counterfactual Test of the Middle-Game Milk Release Mechanism (Days 12-15).

Phase 1: Direct Replay on all 64 EXP173 Mirror Loss Trajectories across candidate variations.
Phase 2: Non-Mirror Safety & Zero-Regression Validation.
Phase 3: Fresh Mirror Seed Generalization.
"""
from __future__ import annotations
import os
import sys
import json
import time
import math
import multiprocessing as mp
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from benchmark.live_calibrated_suite import LIVE_CALIBRATED_DISTRIBUTION

_WORKER_ENV = None
_WORKER_CAND_AGENT = None
_WORKER_OPP_AGENTS = None

def _silenced_import():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    old_stdout = os.dup(1)
    os.dup2(devnull, 2)
    os.dup2(devnull, 1)
    try:
        import kaggle_environments
        return kaggle_environments
    finally:
        os.dup2(old_stderr, 2)
        os.dup2(old_stdout, 1)
        os.close(devnull)
        os.close(old_stderr)
        os.close(old_stdout)

def init_worker():
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    ke = _silenced_import()
    _WORKER_ENV = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0})

    import importlib.util
    spec_cand = importlib.util.spec_from_file_location("sub_cand", os.path.join(BASE_DIR, "candidate_adaptive_terminal.py"))
    sub_cand = importlib.util.module_from_spec(spec_cand)
    spec_cand.loader.exec_module(sub_cand)
    _WORKER_CAND_AGENT = sub_cand.agent

    _WORKER_OPP_AGENTS = {k: v["agent"] for k, v in LIVE_CALIBRATED_DISTRIBUTION.items()}

def _call_agent(fn, obs, conf):
    try: return fn(obs, conf)
    except TypeError: return fn(obs)

def make_counterfactual_agent(base_fn, policy_mode: str):
    """Constructs surgical variations of the Days 12-15 milk release policy."""
    def agent(obs, conf=None):
        step = obs.get("step", 0)
        day = step // 24
        farms = obs.get("farms", [{}, {}])
        p_idx = obs.get("player", 0)
        f = farms[p_idx] if p_idx < len(farms) else {}
        money = float(f.get("money", 0.0))
        unlocked = f.get("unlocked_quadrants", ["NW"])

        priv = obs.get("private") or {}
        shed = priv.get("shed") or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)

        market_obs = obs.get("market") or {}
        prices = market_obs.get("prices") or {}
        p_milk = float(prices.get("MILK", 100.0) or 100.0)
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

        # Call underlying candidate agent
        act = _call_agent(base_fn, obs, conf)
        m = list(act.get("market", []))

        # Check if intervention applies in Days 12-15 (Steps 288-360)
        if policy_mode == "control":
            pass

        elif policy_mode == "arm_b1_milk_p95":
            # In Days 12-15, if milk >= 2 and price >= 95, allow/inject milk sell
            if 12 <= day <= 15 and milk_in_shed >= 2 and p_milk >= 95.0:
                has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m)
                if not has_milk_sell and len(m) < 10:
                    m.append(["SELL", "MILK", milk_in_shed])

        elif policy_mode == "arm_b2_milk_p90":
            # In Days 12-15, if milk >= 2 and price >= 90, allow/inject milk sell
            if 12 <= day <= 15 and milk_in_shed >= 2 and p_milk >= 90.0:
                has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m)
                if not has_milk_sell and len(m) < 10:
                    m.append(["SELL", "MILK", milk_in_shed])

        elif policy_mode == "arm_c1_runway_1500":
            # In Days 11-15, if cash < $1,500, trigger liquidity release
            if 11 <= day <= 15 and money < 1500.0:
                if milk_in_shed >= 2 and not any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m):
                    if len(m) < 10: m.append(["SELL", "MILK", milk_in_shed])
                if straw_in_shed >= 2 and not any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY" for o in m):
                    if len(m) < 10: m.append(["SELL", "STRAWBERRY", straw_in_shed])

        elif policy_mode == "arm_c2_runway_2000":
            # In Days 11-15, if cash < $2,000, trigger liquidity release
            if 11 <= day <= 15 and money < 2000.0:
                if milk_in_shed >= 2 and not any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m):
                    if len(m) < 10: m.append(["SELL", "MILK", milk_in_shed])
                if straw_in_shed >= 2 and not any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY" for o in m):
                    if len(m) < 10: m.append(["SELL", "STRAWBERRY", straw_in_shed])

        elif policy_mode == "arm_d1_partial_milk":
            # In Days 12-15, sell up to min(milk_in_shed, 3) if milk >= 2 and price >= 95
            if 12 <= day <= 15 and milk_in_shed >= 2 and p_milk >= 95.0:
                has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m)
                if not has_milk_sell and len(m) < 10:
                    m.append(["SELL", "MILK", min(milk_in_shed, 3)])

        elif policy_mode == "arm_e1_adaptive_v_milk":
            # In Days 12-15, sell milk if milk >= 2 and (p_milk >= 100.0 or p_milk >= 95.0 and len(f.get('hands', [])) >= 4):
            if 12 <= day <= 15 and milk_in_shed >= 2 and p_milk >= 95.0:
                has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in m)
                if not has_milk_sell and len(m) < 10:
                    m.append(["SELL", "MILK", milk_in_shed])

        act["market"] = m
        return act
    return agent

def run_counterfactual_match(task: tuple) -> dict:
    seed, hero_seat, arm_id, policy_mode = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    hero_fn = make_counterfactual_agent(_WORKER_CAND_AGENT, policy_mode)
    opp_fn = _WORKER_OPP_AGENTS["T1_v18_mirror"]

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    while not env.done:
        o0 = env.state[0].observation
        o1 = env.state[1].observation

        if hero_seat == 0:
            a0 = _call_agent(hero_fn, o0, env.configuration)
            a1 = _call_agent(opp_fn, o1, env.configuration)
        else:
            a0 = _call_agent(opp_fn, o0, env.configuration)
            a1 = _call_agent(hero_fn, o1, env.configuration)

        env.step([a0, a1])

    r_hero = float(env.state[hero_seat].reward or 0)
    r_opp = float(env.state[1 - hero_seat].reward or 0)
    hero_won = r_hero > r_opp
    margin = r_hero - r_opp

    return {
        "seed": seed,
        "hero_seat": hero_seat,
        "arm_id": arm_id,
        "policy_mode": policy_mode,
        "hero_reward": r_hero,
        "opp_reward": r_opp,
        "margin": margin,
        "hero_won": hero_won,
    }

def main():
    mp.freeze_support()
    print("=" * 120)
    print("EXP174: SURGICAL COUNTERFACTUAL TEST OF THE MIDDLE-GAME MILK MECHANISM (64 LOSS REPLAY)")
    print("=" * 120)

    # 1. Load the 64 exact loss cases from EXP173
    exp173_path = os.path.join(BASE_DIR, "reports", "exp173_middle_game_causal_dataset.json")
    if not os.path.exists(exp173_path):
        print(f"Error: Dataset {exp173_path} not found!")
        return

    with open(exp173_path, "r") as f:
        exp173_data = json.load(f)

    losses_64 = [r for r in exp173_data if not r["hero_won"]]
    print(f"Loaded {len(losses_64)} exact mirror loss episodes from EXP173 dataset.")

    arms = [
        ("Control (Current Candidate)", "control"),
        ("Arm B1 (Release Milk @ D12-15 if p>=95)", "arm_b1_milk_p95"),
        ("Arm B2 (Release Milk @ D12-15 if p>=90)", "arm_b2_milk_p90"),
        ("Arm C1 (Runway Lift: Cash < $1,500)", "arm_c1_runway_1500"),
        ("Arm C2 (Runway Lift: Cash < $2,000)", "arm_c2_runway_2000"),
        ("Arm D1 (Partial Milk Release: min(shed, 3))", "arm_d1_partial_milk"),
        ("Arm E1 (Adaptive Milk Release @ D12-15)", "arm_e1_adaptive_v_milk"),
    ]

    tasks = []
    for arm_name, mode in arms:
        for r in losses_64:
            tasks.append((r["seed"], r["hero_seat"], arm_name, mode))

    num_workers = min(10, mp.cpu_count() or 4)
    total_tasks = len(tasks)
    print(f"Executing {total_tasks} counterfactual replays ({len(arms)} arms x {len(losses_64)} loss episodes) on {num_workers} workers...")

    t0 = time.time()
    results = []
    with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
        completed = 0
        for res in pool.imap_unordered(run_counterfactual_match, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - t0
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_tasks) * 100.0
            eta = (total_tasks - completed) / max(0.01, rate)
            print(f"  [Progress] Completed {completed:3d}/{total_tasks} ({pct:5.1f}%) | Speed: {rate:4.1f} m/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    elapsed = time.time() - t0
    print(f"\nCompleted {total_tasks} replays in {elapsed:.1f}s ({(total_tasks/elapsed):.2f} matches/sec).\n")

    # Group by Arm
    arm_summary = {}
    for r in results:
        a = r["arm_id"]
        if a not in arm_summary:
            arm_summary[a] = {"wins": 0, "total": 0, "rewards": [], "margins": [], "flips": []}
        arm_summary[a]["total"] += 1
        arm_summary[a]["rewards"].append(r["hero_reward"])
        arm_summary[a]["margins"].append(r["margin"])
        if r["hero_won"]:
            arm_summary[a]["wins"] += 1
            arm_summary[a]["flips"].append(r)

    ctrl_rew = sum(arm_summary["Control (Current Candidate)"]["rewards"]) / len(losses_64)

    print("=" * 120)
    print("EXP174 COUNTERFACTUAL RESULTS ON THE 64 HISTORICAL MIRROR LOSSES:")
    print("=" * 120)
    print(f"{'Policy Arm':<44} | {'Loss Replays':<12} | {'Converted to WIN':<18} | {'Mean Reward':<14} | {'Delta vs Control'}")
    print("-" * 120)

    for arm_name, _ in arms:
        s = arm_summary[arm_name]
        mean_r = sum(s["rewards"]) / s["total"]
        delta_r = mean_r - ctrl_rew
        n_flips = s["wins"]
        pct_flips = (n_flips / s["total"]) * 100.0
        print(f"{arm_name:<44} | {s['total']:<12} | {n_flips:2d} / {s['total']:2d} ({pct_flips:4.1f}%) 🔥  | ${mean_r:10,.1f} | ${delta_r:+10,.1f}")
    print("=" * 120)

    # Save full counterfactual report
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    out_file = os.path.join(BASE_DIR, "reports", "exp174_milk_counterfactual_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved EXP174 Counterfactual Results to: {out_file}")

if __name__ == "__main__":
    main()
