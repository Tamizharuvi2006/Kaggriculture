"""EXP171: Comprehensive 4th-Land (SE Quadrant) Economic Viability & Counterfactual Mine.

Evaluates the break-even frontier, worker allocation, and economic feasibility
of the $4,000 SE quadrant across 7 realistic population archetypes.
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
    try:
        return fn(obs, conf)
    except TypeError:
        return fn(obs)

def make_experiment_agent(base_fn, arm_config: dict):
    """Wraps candidate agent with explicit 4th quadrant management."""
    allow_4th = arm_config.get("allow_4th", False)
    min_day = arm_config.get("min_day", 14)
    min_cash = arm_config.get("min_cash", 6000)
    extra_hand = arm_config.get("extra_hand", False)

    def agent(obs, conf=None):
        step = obs.get("step", 0)
        day = step // 24
        farms = obs.get("farms", [{}, {}])
        p_idx = obs.get("player", 0)
        f = farms[p_idx] if p_idx < len(farms) else {}
        money = float(f.get("money", 0.0))
        unlocked = f.get("unlocked_quadrants", ["NW"])

        act = _call_agent(base_fn, obs, conf)
        m = list(act.get("market", []))
        farmer_act = list(act.get("farmer", ["PASS"]))
        hands_act = [list(h) for h in act.get("hands", [])]

        if allow_4th and len(unlocked) == 3:
            if day >= min_day and money >= min_cash:
                has_buy_land = any(len(o) >= 1 and o[0] == "BUY_LAND" for o in m)
                if not has_buy_land and len(m) < 10:
                    m.append(["BUY_LAND"])
                    if extra_hand and len(m) < 10:
                        m.append(["HIRE"])

        elif not allow_4th:
            m = [o for o in m if not (len(o) >= 1 and o[0] == "BUY_LAND" and len(unlocked) >= 3)]

        act["market"] = m
        return act
    return agent

def run_match_task(task: tuple) -> dict:
    seed, opp_key, arm_name, arm_config = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    hero_fn = make_experiment_agent(_WORKER_CAND_AGENT, arm_config)
    opp_fn = _WORKER_OPP_AGENTS[opp_key]
    opp_cluster = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["cluster_name"]

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    land4_step = None
    while not env.done:
        o0, o1 = env.state[0].observation, env.state[1].observation
        f0 = (o0.get("farms") or [{}])[0]
        if len(f0.get("unlocked_quadrants", [])) == 4 and land4_step is None:
            land4_step = env.state[0].observation.get("step", 0)

        a0 = _call_agent(hero_fn, o0, env.configuration)
        a1 = _call_agent(opp_fn, o1, env.configuration)
        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0)
    r1 = float(env.state[1].reward or 0)

    return {
        "seed": seed,
        "opp_key": opp_key,
        "opp_cluster": opp_cluster,
        "arm": arm_name,
        "hero_reward": r0,
        "opp_reward": r1,
        "margin": r0 - r1,
        "win": r0 > r1,
        "land4_step": land4_step,
    }

def main():
    mp.freeze_support()
    print("=" * 120)
    print("EXP171: 4TH-LAND (SE QUADRANT) ECONOMIC VIABILITY & BREAK-EVEN FRONTIER STUDY")
    print("=" * 120)

    num_workers = min(10, mp.cpu_count() or 4)
    seeds = list(range(91001, 91021)) # 20 seeds x 7 archetypes = 140 matches per arm
    opp_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())

    arms = [
        ("Control (3 Quadrants Only)", {"allow_4th": False}),
        ("SE @ Day 10 (Cash >= $5k)", {"allow_4th": True, "min_day": 10, "min_cash": 5000, "extra_hand": False}),
        ("SE @ Day 14 (Cash >= $6k)", {"allow_4th": True, "min_day": 14, "min_cash": 6000, "extra_hand": False}),
        ("SE @ Day 14 (Cash >= $6k + Hire Hand)", {"allow_4th": True, "min_day": 14, "min_cash": 6000, "extra_hand": True}),
        ("SE @ Day 18 (Cash >= $7k)", {"allow_4th": True, "min_day": 18, "min_cash": 7000, "extra_hand": False}),
        ("SE @ Day 20 (Cash >= $8k)", {"allow_4th": True, "min_day": 20, "min_cash": 8000, "extra_hand": False}),
        ("SE @ Day 22 (Cash >= $10k)", {"allow_4th": True, "min_day": 22, "min_cash": 10000, "extra_hand": False}),
    ]

    tasks = []
    for arm_name, cfg in arms:
        for s in seeds:
            for opp in opp_keys:
                tasks.append((s, opp, arm_name, cfg))

    total_matches = len(tasks)
    print(f"Allocating {num_workers} parallel workers for {len(arms)} arms x {len(seeds)} seeds x {len(opp_keys)} opponents = {total_matches} matches...")

    t0 = time.time()
    results = []
    with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
        completed = 0
        for res in pool.imap_unordered(run_match_task, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - t0
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_matches) * 100.0
            eta = (total_matches - completed) / max(0.01, rate)
            print(f"  [Progress] Completed {completed:4d}/{total_matches} ({pct:5.1f}%) | Speed: {rate:4.1f} m/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    t1 = time.time()
    print(f"\nCompleted {total_matches} simulations in {t1-t0:.1f}s ({(total_matches/(t1-t0)):.2f} matches/sec).\n")

    # Group by arm
    arm_data = {}
    for r in results:
        a = r["arm"]
        if a not in arm_data:
            arm_data[a] = {"rewards": [], "margins": [], "wins": 0, "total": 0, "buys": 0}
        arm_data[a]["rewards"].append(r["hero_reward"])
        arm_data[a]["margins"].append(r["margin"])
        if r["win"]: arm_data[a]["wins"] += 1
        arm_data[a]["total"] += 1
        if r["land4_step"] is not None:
            arm_data[a]["buys"] += 1

    ctrl_rew = sum(arm_data["Control (3 Quadrants Only)"]["rewards"]) / len(arm_data["Control (3 Quadrants Only)"]["rewards"])
    ctrl_wr = (arm_data["Control (3 Quadrants Only)"]["wins"] / arm_data["Control (3 Quadrants Only)"]["total"]) * 100.0

    print("=" * 120)
    print("4TH-LAND (SE QUADRANT) BREAK-EVEN & PROFITABILITY FRONTIER SUMMARY:")
    print("=" * 120)
    print(f"{'Policy Arm':<38} | {'Matches':<8} | {'SE Buys':<8} | {'Win Rate':<14} | {'Mean Wealth':<14} | {'Delta vs Control':<20}")
    print("-" * 120)
    for a, s in arm_data.items():
        m_rew = sum(s["rewards"]) / s["total"]
        wr = (s["wins"] / s["total"]) * 100.0
        delta = m_rew - ctrl_rew
        verdict = "✅ PROFITABLE" if delta > 0 else "❌ VALUE DESTROYING"
        print(f"{a:<38} | {s['total']:<8} | {s['buys']:<8} | {wr:5.1f}% ({s['wins']:3d}/{s['total']:3d}) | ${m_rew:10,.1f} | ${delta:+10,.1f} ({verdict})")
    print("=" * 120)

    # Save report
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(BASE_DIR, "reports", "exp171_4th_land_economic_frontier.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Full Frontier Dataset to: {report_path}")

if __name__ == "__main__":
    main()
