"""EXP172: Terminal Comeback Flip & Middle-Game Deficit Localization Mine.

Profiles the exact turn-by-turn cash flows during the terminal window (Steps 696-720)
and localizes where unrecoverable middle-game deficits originate across 7 population archetypes.
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

def compute_wealth_and_breakdown(obs: Dict[str, Any], player_idx: int) -> tuple[float, float, float, dict]:
    """Returns (total_wealth, cash, field_val, shed_inventory)."""
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

    return cash + shed_val + field_val, cash, field_val, dict(inv)

def _call_agent(fn, obs, conf):
    try: return fn(obs, conf)
    except TypeError: return fn(obs)

def run_match_telemetry(task: tuple) -> Dict[str, Any]:
    seed, opp_key = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    hero_fn = _WORKER_CAND_AGENT
    opp_fn = _WORKER_OPP_AGENTS[opp_key]
    opp_cluster = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["cluster_name"]

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    # Target Checkpoint steps
    checkpoints = [120, 240, 360, 480, 600, 650, 680, 696, 700, 705, 710, 715, 716, 717, 718, 719, 720]
    telemetry = {}

    final_turns_log = []

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        o0 = env.state[0].observation
        o1 = env.state[1].observation

        w0, c0, f0, inv0 = compute_wealth_and_breakdown(o0, 0)
        w1, c1, f1, inv1 = compute_wealth_and_breakdown(o1, 1)

        if step in checkpoints:
            telemetry[f"Step_{step}"] = {
                "hero_wealth": w0,
                "opp_wealth": w1,
                "wealth_gap": w0 - w1,
                "hero_cash": c0,
                "opp_cash": c1,
                "cash_gap": c0 - c1,
                "hero_field": f0,
                "opp_field": f1,
                "hero_shed_straw": inv0.get("STRAWBERRY", 0),
                "hero_shed_milk": inv0.get("MILK", 0),
                "hero_hands": len((o0.get("farms") or [{}])[0].get("hands", [])),
                "opp_hands": len((o1.get("farms") or [{}])[1].get("hands", [])),
            }

        a0 = _call_agent(hero_fn, o0, env.configuration)
        a1 = _call_agent(opp_fn, o1, env.configuration)

        if step >= 715:
            final_turns_log.append({
                "step": step,
                "hero_cash_before": c0,
                "opp_cash_before": c1,
                "hero_market_act": a0.get("market", []),
                "hero_hands_acts": [list(h) for h in a0.get("hands", [])],
            })

        env.step([a0, a1])

    final_hero_reward = float(env.state[0].reward or 0)
    final_opp_reward = float(env.state[1].reward or 0)
    hero_won = final_hero_reward > final_opp_reward
    final_margin = final_hero_reward - final_opp_reward

    # Record final step 720 state
    telemetry["Step_720"] = {
        "hero_wealth": final_hero_reward,
        "opp_wealth": final_opp_reward,
        "wealth_gap": final_margin,
        "hero_cash": final_hero_reward,
        "opp_cash": final_opp_reward,
        "cash_gap": final_margin,
        "hero_field": 0.0,
        "opp_field": 0.0,
    }

    # Analyze Cohort:
    # 1. Natural Win: Behind at step 696? No. Behind at 716? No. Won at 720.
    # 2. Terminal Comeback Flip: Behind at step 696 OR 716, but Won at 720.
    # 3. Unconverted Deficit Loss: Lost at 720.
    cash_gap_696 = telemetry.get("Step_696", {}).get("cash_gap", 0.0)
    cash_gap_716 = telemetry.get("Step_716", {}).get("cash_gap", 0.0)
    wealth_gap_696 = telemetry.get("Step_696", {}).get("wealth_gap", 0.0)

    terminal_cash_jump = final_hero_reward - telemetry.get("Step_696", {}).get("hero_cash", final_hero_reward)
    opp_terminal_cash_jump = final_opp_reward - telemetry.get("Step_696", {}).get("opp_cash", final_opp_reward)
    net_terminal_advantage = terminal_cash_jump - opp_terminal_cash_jump

    is_flip = False
    if hero_won and (cash_gap_696 < 0 or cash_gap_716 < 0):
        cohort = "Terminal_Comeback_Flip"
        is_flip = True
    elif hero_won:
        cohort = "Natural_Win"
    else:
        cohort = "Unconverted_Deficit_Loss"

    # For losses: identify where lead was permanently lost
    turning_point = "None (Won)"
    if not hero_won:
        epochs = [0, 120, 240, 360, 480, 600, 696]
        for prev_s, next_s in zip(epochs[:-1], epochs[1:]):
            g_prev = telemetry.get(f"Step_{prev_s}", {}).get("wealth_gap", 0.0)
            g_next = telemetry.get(f"Step_{next_s}", {}).get("wealth_gap", 0.0)
            if g_next < 0 and g_prev >= 0:
                turning_point = f"Steps_{prev_s}_{next_s}"
                break
        if turning_point == "None (Won)":
            turning_point = "Step_0_Opening_Deficit"

    return {
        "seed": seed,
        "opp_key": opp_key,
        "opp_cluster": opp_cluster,
        "hero_won": hero_won,
        "final_margin": final_margin,
        "cohort": cohort,
        "is_flip": is_flip,
        "cash_gap_696": cash_gap_696,
        "cash_gap_716": cash_gap_716,
        "wealth_gap_696": wealth_gap_696,
        "terminal_cash_jump": terminal_cash_jump,
        "opp_terminal_cash_jump": opp_terminal_cash_jump,
        "net_terminal_advantage": net_terminal_advantage,
        "turning_point": turning_point,
        "telemetry": telemetry,
        "final_turns_log": final_turns_log,
    }

def main():
    mp.freeze_support()
    print("=" * 120)
    print("EXP172: TERMINAL COMEBACK FLIP & MIDDLE-GAME DEFICIT LOCALIZATION MINE")
    print("=" * 120)

    num_workers = min(10, mp.cpu_count() or 4)
    seeds = list(range(91001, 91051)) # 50 seeds x 7 archetypes = 350 matches
    opp_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())

    tasks = [(s, opp) for s in seeds for opp in opp_keys]
    total_matches = len(tasks)

    print(f"Allocating {num_workers} parallel workers for {len(seeds)} seeds x {len(opp_keys)} archetypes = {total_matches} matches...")

    t0 = time.time()
    results = []
    with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
        completed = 0
        for res in pool.imap_unordered(run_match_telemetry, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - t0
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_matches) * 100.0
            eta = (total_matches - completed) / max(0.01, rate)
            print(f"  [Progress] Completed {completed:4d}/{total_matches} ({pct:5.1f}%) | Speed: {rate:4.1f} m/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    elapsed = time.time() - t0
    print(f"\nCompleted {total_matches} matches in {elapsed:.1f}s ({(total_matches/elapsed):.2f} matches/sec).\n")

    # Cohort Analysis
    total = len(results)
    wins = [r for r in results if r["hero_won"]]
    flips = [r for r in results if r["cohort"] == "Terminal_Comeback_Flip"]
    losses = [r for r in results if not r["hero_won"]]
    nat_wins = [r for r in results if r["cohort"] == "Natural_Win"]

    print("=" * 120)
    print("MATCH COHORT BREAKDOWN:")
    print("=" * 120)
    print(f"  Total Matches Tested         : {total}")
    print(f"  Overall Win Rate             : {len(wins)} / {total} ({len(wins)/total*100:.1f}%)")
    print(f"  Natural Wire-to-Wire Wins    : {len(nat_wins)} ({len(nat_wins)/total*100:.1f}%)")
    print(f"  🔥 Terminal Comeback Flips   : {len(flips)} ({len(flips)/total*100:.1f}% of matches, {len(flips)/max(1, len(wins))*100:.1f}% of ALL wins!)")
    print(f"  ❌ Unconverted Deficit Losses: {len(losses)} ({len(losses)/total*100:.1f}%)")
    print("=" * 120)

    # Terminal Cash Jump Statistics
    jumps = [r["terminal_cash_jump"] for r in results]
    mean_jump = sum(jumps) / len(jumps)
    median_jump = sorted(jumps)[len(jumps)//2]
    max_jump = max(jumps)
    min_jump = min(jumps)

    advs = [r["net_terminal_advantage"] for r in results]
    mean_adv = sum(advs) / len(advs)

    print("\n" + "=" * 120)
    print("DAY 30 TERMINAL INTERVENTION VALUE CREATION (Steps 696 -> 720):")
    print("=" * 120)
    print(f"  Mean Hero Cash Jump (Steps 696-720)       : +${mean_jump:10,.1f}")
    print(f"  Median Hero Cash Jump                     : +${median_jump:10,.1f}")
    print(f"  Range of Hero Terminal Realization        : +${min_jump:10,.1f} to +${max_jump:10,.1f}")
    print(f"  Mean Net Advantage Over Opponent Terminal : +${mean_adv:10,.1f}")
    print("=" * 120)

    # Flip Deep-Dive
    if flips:
        print("\n" + "=" * 120)
        print("SAMPLE TERMINAL COMEBACK FLIPS (Behind at Step 716 -> WON at Step 720):")
        print("=" * 120)
        print(f"{'Seed':<8} | {'Opponent Key':<24} | {'Cash Gap @ 716':<16} | {'Terminal Jump':<16} | {'Final Margin':<14}")
        print("-" * 120)
        for r in flips[:10]:
            print(f"{r['seed']:<8} | {r['opp_key']:<24} | ${r['cash_gap_716']:+10,.1f}     | +${r['terminal_cash_jump']:10,.1f}   | ${r['final_margin']:+10,.1f}")
        print("=" * 120)

    # Loss Localization
    if losses:
        print("\n" + "=" * 120)
        print("UNCONVERTED LOSSES: CAUSAL DEFICIT ORIGINATION (Where Fatal Gap Developed):")
        print("=" * 120)
        tp_counts = {}
        for r in losses:
            tp = r["turning_point"]
            tp_counts[tp] = tp_counts.get(tp, 0) + 1

        phase_descriptions = {
            "Steps_0_120": "Days 1-5 (Opening / 1st Quadrant Setup)",
            "Steps_120_240": "Days 6-10 (Land #2 Purchase & Strawberry Expansion)",
            "Steps_240_360": "Days 11-15 (Land #3 / Cow Setup)",
            "Steps_360_480": "Days 16-20 (Mid-Game Strawberry & Milk Scaling)",
            "Steps_480_600": "Days 21-25 (Late Scaling / Peak Inventory)",
            "Steps_600_696": "Days 26-29 (Pre-Terminal Day 29 Setup)",
            "Step_0_Opening_Deficit": "Step 0 Opening RNG / Deficit",
        }

        print(f"{'Game Phase':<30} | {'Loss Count':<12} | {'% of Losses':<16} | {'Avg Deficit @ 696':<20} | {'Phase Description'}")
        print("-" * 120)
        for tp, cnt in sorted(tp_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (cnt / len(losses)) * 100.0
            cohort_losses = [r for r in losses if r["turning_point"] == tp]
            avg_def = sum(r["cash_gap_696"] for r in cohort_losses) / len(cohort_losses)
            desc = phase_descriptions.get(tp, tp)
            print(f"{tp:<30} | {cnt:<12} | {pct:5.1f}% {'█'*int(pct/5):<10} | ${avg_def:+12,.1f}       | {desc}")
        print("=" * 120)

    # Save full dataset
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(BASE_DIR, "reports", "exp172_terminal_flip_and_deficit_telemetry.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Comprehensive Telemetry Dataset to: {report_path}")

if __name__ == "__main__":
    main()
