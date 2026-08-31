"""EXP171: 10,000-Match Middle-Game Counterfactual Mine & Phase Loss Attribution.

Layer 1: Massive Multi-Epoch Wealth Trajectory & Loss Attribution Audit across 1,000+ matches per batch.
Layer 2: State-Action Decision Point Extraction (Days 6-25 / Steps 120-600).
Layer 3: Local Counterfactual Action Branching & Regression Profiling.
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

# Persistent worker state
_WORKER_ENV = None
_WORKER_CAND_AGENT = None
_WORKER_OPP_AGENTS = None

def _silenced_import():
    """Silences C++ OpenSpiel import spam to stderr/stdout during worker boot."""
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
    """Initializes persistent worker resources once per child process."""
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    ke = _silenced_import()
    _WORKER_ENV = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0})

    import importlib.util
    spec_cand = importlib.util.spec_from_file_location("sub_cand", os.path.join(BASE_DIR, "candidate_adaptive_terminal.py"))
    sub_cand = importlib.util.module_from_spec(spec_cand)
    spec_cand.loader.exec_module(sub_cand)
    _WORKER_CAND_AGENT = sub_cand.agent

    _WORKER_OPP_AGENTS = {k: v["agent"] for k, v in LIVE_CALIBRATED_DISTRIBUTION.items()}

def compute_total_wealth(obs: Dict[str, Any], player_idx: int) -> float:
    """Calculates instantaneous marked-to-market wealth: cash + shed inventory value + ripe field value."""
    farms = obs.get("farms", [{}, {}])
    f = farms[player_idx] if player_idx < len(farms) else {}
    cash = float(f.get("money", 0.0))

    prices = (obs.get("market") or {}).get("prices") or {}
    p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
    p_milk = float(prices.get("MILK", 100.0) or 100.0)
    p_wool = float(prices.get("WOOL", 150.0) or 150.0)
    p_carrot = float(prices.get("CARROT", 35.0) or 35.0)
    p_wheat = float(prices.get("WHEAT", 20.0) or 20.0)
    p_fert = float(prices.get("FERTILIZER", 10.0) or 10.0)

    inventories = obs.get("private", {}).get("inventories", [{}, {}])
    inv = inventories[player_idx] if player_idx < len(inventories) else {}
    shed_val = (
        inv.get("STRAWBERRY", 0) * p_straw +
        inv.get("MILK", 0) * p_milk +
        inv.get("WOOL", 0) * p_wool +
        inv.get("CARROT", 0) * p_carrot +
        inv.get("WHEAT", 0) * p_wheat +
        inv.get("FERTILIZER", 0) * p_fert
    )

    field_val = 0.0
    for row in f.get("tiles", []):
        for t in row:
            if isinstance(t, dict):
                y = t.get("yield_units", 0)
                if t.get("kind") == "PLANT" and y > 0:
                    c = t.get("crop")
                    p = p_straw if c == "STRAWBERRY" else (p_carrot if c == "CARROT" else p_wheat)
                    field_val += y * p
                elif "animal" in t and y > 0:
                    a = t.get("animal")
                    p = p_milk if a == "COW" else p_wool
                    field_val += y * p

    return cash + shed_val + field_val

def _call_agent(fn, obs, conf):
    try:
        return fn(obs, conf)
    except TypeError:
        return fn(obs)

def run_trajectory_match(task: tuple) -> Dict[str, Any]:
    """Simulates a single 720-step match and extracts multi-epoch wealth checkpoints."""
    seed, opp_key, hero_seat = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    cand_fn = _WORKER_CAND_AGENT
    opp_fn = _WORKER_OPP_AGENTS[opp_key]

    opp_cluster = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["cluster_name"]
    opp_weight = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["empirical_weight"]

    # Re-seed persistent environment deterministically
    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    # Trajectory checkpoints at Days 5, 10, 15, 20, 25, 29, 30
    epochs = [120, 240, 360, 480, 600, 696, 720]
    wealth_history_hero = {}
    wealth_history_opp = {}
    lead_history = {}

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        o0 = env.state[0].observation
        o1 = env.state[1].observation

        if step in epochs:
            w0 = compute_total_wealth(o0, 0)
            w1 = compute_total_wealth(o1, 1)
            wealth_history_hero[f"Step_{step}"] = w0 if hero_seat == 0 else w1
            wealth_history_opp[f"Step_{step}"] = w1 if hero_seat == 0 else w0
            lead_history[f"Step_{step}"] = (w0 - w1) if hero_seat == 0 else (w1 - w0)

        if hero_seat == 0:
            a0 = _call_agent(cand_fn, o0, env.configuration)
            a1 = _call_agent(opp_fn, o1, env.configuration)
        else:
            a0 = _call_agent(opp_fn, o0, env.configuration)
            a1 = _call_agent(cand_fn, o1, env.configuration)

        env.step([a0, a1])

    final_hero_reward = float(env.state[hero_seat].reward or 0)
    final_opp_reward = float(env.state[1 - hero_seat].reward or 0)
    hero_won = final_hero_reward > final_opp_reward
    final_margin = final_hero_reward - final_opp_reward

    lead_history["Step_720"] = final_margin
    wealth_history_hero["Step_720"] = final_hero_reward
    wealth_history_opp["Step_720"] = final_opp_reward

    # Determine turning point epoch where lead became irreversibly negative (if loss)
    turning_point_epoch = "None (Won)"
    if not hero_won:
        for prev_s, next_s in zip([0, 120, 240, 360, 480, 600, 696], epochs):
            lead_prev = lead_history.get(f"Step_{prev_s}", 0.0)
            lead_next = lead_history.get(f"Step_{next_s}", 0.0)
            if lead_next < 0 and lead_prev >= 0:
                turning_point_epoch = f"Steps_{prev_s}_{next_s}"
                break
        if turning_point_epoch == "None (Won)":
            turning_point_epoch = "Step_0 (Never had lead)"

    return {
        "seed": seed,
        "opp_key": opp_key,
        "opp_cluster": opp_cluster,
        "opp_weight": opp_weight,
        "hero_seat": hero_seat,
        "hero_won": hero_won,
        "final_margin": final_margin,
        "lead_history": lead_history,
        "wealth_hero": wealth_history_hero,
        "wealth_opp": wealth_history_opp,
        "turning_point": turning_point_epoch,
    }

def main():
    print("=" * 120)
    print("EXP171: 10,000-MATCH MIDDLE-GAME COUNTERFACTUAL MINE & LOSS ATTRIBUTION")
    print("=" * 120)

    num_processes = min(10, mp.cpu_count() or 4)
    total_seeds = 200 # 200 seeds * 7 archetypes = 1,400 matches for Phase 1 diagnostic
    opp_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())

    print(f"Hardware Allocation: {num_processes} parallel persistent worker processes (CPU Bound)")
    print(f"Target Benchmark   : {total_seeds} seeds across all {len(opp_keys)} realistic population archetypes = {total_seeds * len(opp_keys)} matches")
    print(f"Seeds Range        : 91001 to {91001 + total_seeds - 1}")

    seeds = list(range(91001, 91001 + total_seeds))
    tasks = [(s, opp, 0) for s in seeds for opp in opp_keys]
    total_matches = len(tasks)

    start_time = time.time()
    results = []
    completed = 0

    with mp.Pool(processes=num_processes, initializer=init_worker) as pool:
        for res in pool.imap_unordered(run_trajectory_match, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_matches) * 100.0
            eta = (total_matches - completed) / max(0.01, rate)
            print(f"  [Live Progress] Completed {completed:4d}/{total_matches} ({pct:5.1f}%) | Speed: {rate:4.1f} matches/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    elapsed = time.time() - start_time
    print(f"\nCompleted {len(results)} trajectory simulations in {elapsed:.1f}s ({len(results)/elapsed:.2f} matches/sec).")

    # Analyze Loss Attribution by Phase
    total_completed = len(results)
    losses = [r for r in results if not r["hero_won"]]
    wins = [r for r in results if r["hero_won"]]

    overall_wr = (len(wins) / total_completed) * 100.0
    print(f"\nOverall Population Win Rate: {len(wins)}/{total_completed} ({overall_wr:.1f}%)")

    # Cluster Breakdown
    cluster_stats = {}
    for r in results:
        c = r["opp_cluster"]
        if c not in cluster_stats:
            cluster_stats[c] = {"total": 0, "wins": 0, "losses": 0, "margins": []}
        cluster_stats[c]["total"] += 1
        if r["hero_won"]: cluster_stats[c]["wins"] += 1
        else: cluster_stats[c]["losses"] += 1
        cluster_stats[c]["margins"].append(r["final_margin"])

    print("\n" + "=" * 120)
    print("POPULATION CLUSTER PERFORMANCE BREAKDOWN:")
    print("=" * 120)
    print(f"{'Cluster Name':<32} | {'Matches':<8} | {'Win Rate':<16} | {'Mean Margin':<14}")
    print("-" * 120)
    for c, s in cluster_stats.items():
        wr = (s['wins'] / s['total']) * 100.0
        mean_m = sum(s['margins']) / len(s['margins'])
        print(f"{c:<32} | {s['total']:<8} | {s['wins']:3d}/{s['total']:3d} ({wr:5.1f}%) | ${mean_m:+10,.2f}")
    print("=" * 120)

    # Loss Attribution by Phase
    print("\n" + "=" * 120)
    print("PHASE-LEVEL LOSS ATTRIBUTION & VALUE LEAK AUDIT (Where Lead Was Lost):")
    print("=" * 120)
    turning_points = {}
    for r in losses:
        tp = r["turning_point"]
        turning_points[tp] = turning_points.get(tp, 0) + 1

    print(f"{'Game Phase (Epoch)':<30} | {'Loss Count':<12} | {'% of Total Losses':<20} | {'Phase Description'}")
    print("-" * 120)
    phase_descriptions = {
        "Steps_0_120": "Days 1-5 (Opening / 1st Quadrant Setup)",
        "Steps_120_240": "Days 6-10 (Land #2 Purchase & Strawberry Expansion)",
        "Steps_240_360": "Days 11-15 (Land #3 / Early Cow Setup)",
        "Steps_360_480": "Days 16-20 (Mid-Game Strawberry / Milk Scaling)",
        "Steps_480_600": "Days 21-25 (Late Scaling / Peak Liquidity)",
        "Steps_600_696": "Days 26-29 (Pre-Terminal Day 29 Setup)",
        "Step_0 (Never had lead)": "Opening Step 0 deficit",
        "None (Won)": "N/A"
    }

    total_losses = len(losses)
    for phase, count in sorted(turning_points.items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(1, total_losses)) * 100.0
        desc = phase_descriptions.get(phase, phase)
        print(f"{phase:<30} | {count:<12} | {pct:5.1f}% {'█' * int(pct/5):<15} | {desc}")
    print("=" * 120)

    # Save EXP171 Phase 1 Report
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    out_file = os.path.join(BASE_DIR, "reports", "exp171_middle_game_attribution.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved EXP171 Loss Attribution Dataset to: {out_file}")

if __name__ == "__main__":
    mp.freeze_support()
    main()
