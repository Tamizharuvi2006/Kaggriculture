"""EXP173: 10k Middle-Game (Days 6-15 / Steps 120-360) Causal Action & State Divergence Mine.

Phase 1: High-Resolution Telemetry Mining across Days 6-15 on the Live Population Suite.
Phase 2: Pre-Deficit Causal Divergence Localization (State -> Action -> Downstream Delta).
Phase 3: Paired Counterfactual Branching on Identical (Seed, Seat, Opponent) triples.
"""
from __future__ import annotations
import os
import sys
import json
import time
import math
import multiprocessing as mp
from typing import Dict, List, Any, Tuple

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

def compute_detailed_state(obs: Dict[str, Any], player_idx: int) -> dict:
    """Extracts fine-grained economic, production, and tile metrics."""
    farms = obs.get("farms", [{}, {}])
    f = farms[player_idx] if player_idx < len(farms) else {}
    cash = float(f.get("money", 0.0))
    unlocked_quads = len(f.get("unlocked_quadrants", ["NW"]))
    hands_count = len(f.get("hands", []))

    prices = (obs.get("market") or {}).get("prices") or {}
    p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
    p_milk = float(prices.get("MILK", 100.0) or 100.0)
    p_wool = float(prices.get("WOOL", 150.0) or 150.0)
    p_carrot = float(prices.get("CARROT", 35.0) or 35.0)
    p_wheat = float(prices.get("WHEAT", 20.0) or 20.0)
    p_fert = float(prices.get("FERTILIZER", 10.0) or 10.0)

    inventories = obs.get("private", {}).get("inventories", [{}, {}])
    inv = inventories[player_idx] if player_idx < len(inventories) else {}
    shed_straw = inv.get("STRAWBERRY", 0)
    shed_milk = inv.get("MILK", 0)
    shed_fert = inv.get("FERTILIZER", 0)
    shed_wheat = inv.get("WHEAT", 0)

    shed_val = (
        shed_straw * p_straw +
        shed_milk * p_milk +
        inv.get("WOOL", 0) * p_wool +
        inv.get("CARROT", 0) * p_carrot +
        shed_wheat * p_wheat +
        shed_fert * p_fert
    )

    field_val = 0.0
    planted_tiles = 0
    ripe_tiles = 0
    watered_tiles = 0
    tilled_empty = 0
    cow_count = 0

    for row in f.get("tiles", []):
        for t in row:
            if isinstance(t, dict):
                k = t.get("kind")
                y = t.get("yield_units", 0)
                if k == "PLANT":
                    planted_tiles += 1
                    if t.get("watered"): watered_tiles += 1
                    if y > 0:
                        ripe_tiles += 1
                        c = t.get("crop")
                        p = p_straw if c == "STRAWBERRY" else (p_carrot if c == "CARROT" else p_wheat)
                        field_val += y * p
                elif "animal" in t:
                    if t.get("animal") == "COW": cow_count += 1
                    if y > 0:
                        ripe_tiles += 1
                        p = p_milk if t.get("animal") == "COW" else p_wool
                        field_val += y * p
            elif t is None:
                pass

    total_wealth = cash + shed_val + field_val
    return {
        "wealth": total_wealth,
        "cash": cash,
        "shed_val": shed_val,
        "field_val": field_val,
        "unlocked_quads": unlocked_quads,
        "hands_count": hands_count,
        "cows": cow_count,
        "shed_straw": shed_straw,
        "shed_milk": shed_milk,
        "planted_tiles": planted_tiles,
        "ripe_tiles": ripe_tiles,
        "watered_tiles": watered_tiles,
        "p_straw": p_straw,
        "p_milk": p_milk,
    }

def _call_agent(fn, obs, conf):
    try: return fn(obs, conf)
    except TypeError: return fn(obs)

def run_trajectory_mine(task: tuple) -> Dict[str, Any]:
    seed, opp_key, hero_seat = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    hero_fn = _WORKER_CAND_AGENT
    opp_fn = _WORKER_OPP_AGENTS[opp_key]
    opp_cluster = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["cluster_name"]

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    # Step Checkpoints across Days 6-15 (every 24 steps from 120 to 360) + terminal checkpoints
    eval_steps = [120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360, 480, 600, 696, 720]
    eval_steps_set = set(eval_steps)
    step_telemetry = {}

    land2_step = None
    land3_step = None
    first_cow_step = None

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        o0 = env.state[0].observation
        o1 = env.state[1].observation

        o_hero = o0 if hero_seat == 0 else o1
        o_opp = o1 if hero_seat == 0 else o0

        f_hero = (o_hero.get("farms") or [{}, {}])[hero_seat]
        quads = len(f_hero.get("unlocked_quadrants", ["NW"]))
        if quads >= 2 and land2_step is None: land2_step = step
        if quads >= 3 and land3_step is None: land3_step = step

        if step in eval_steps_set:
            s_hero = compute_detailed_state(o_hero, hero_seat)
            s_opp = compute_detailed_state(o_opp, 1 - hero_seat)

            if s_hero["cows"] > 0 and first_cow_step is None:
                first_cow_step = step

            step_telemetry[f"Step_{step}"] = {
                "hero_wealth": s_hero["wealth"],
                "opp_wealth": s_opp["wealth"],
                "wealth_gap": s_hero["wealth"] - s_opp["wealth"],
                "hero_cash": s_hero["cash"],
                "opp_cash": s_opp["cash"],
                "cash_gap": s_hero["cash"] - s_opp["cash"],
                "hero_quads": s_hero["unlocked_quads"],
                "opp_quads": s_opp["unlocked_quads"],
                "hero_hands": s_hero["hands_count"],
                "opp_hands": s_opp["hands_count"],
                "hero_cows": s_hero["cows"],
                "opp_cows": s_opp["cows"],
                "hero_planted": s_hero["planted_tiles"],
                "hero_ripe": s_hero["ripe_tiles"],
                "hero_shed_straw": s_hero["shed_straw"],
                "hero_shed_milk": s_hero["shed_milk"],
                "p_straw": s_hero["p_straw"],
                "p_milk": s_hero["p_milk"],
            }

        if hero_seat == 0:
            a0 = _call_agent(hero_fn, o0, env.configuration)
            a1 = _call_agent(opp_fn, o1, env.configuration)
        else:
            a0 = _call_agent(opp_fn, o0, env.configuration)
            a1 = _call_agent(hero_fn, o1, env.configuration)

        env.step([a0, a1])

    final_hero_reward = float(env.state[hero_seat].reward or 0)
    final_opp_reward = float(env.state[1 - hero_seat].reward or 0)
    hero_won = final_hero_reward > final_opp_reward
    final_margin = final_hero_reward - final_opp_reward

    # Record final reward
    step_telemetry["Step_720"] = {
        "hero_wealth": final_hero_reward,
        "opp_wealth": final_opp_reward,
        "wealth_gap": final_margin,
    }

    # Identify earliest turning point
    turning_point = "None (Won)"
    if not hero_won:
        for prev_s, next_s in zip(eval_steps[:-1], eval_steps[1:]):
            w_prev = step_telemetry.get(f"Step_{prev_s}", {}).get("wealth_gap", 0.0)
            w_next = step_telemetry.get(f"Step_{next_s}", {}).get("wealth_gap", 0.0)
            if w_next < 0 and w_prev >= 0:
                turning_point = f"Step_{next_s}"
                break
        if turning_point == "None (Won)":
            turning_point = "Step_120_or_Earlier"

    return {
        "seed": seed,
        "opp_key": opp_key,
        "opp_cluster": opp_cluster,
        "hero_seat": hero_seat,
        "hero_won": hero_won,
        "final_margin": final_margin,
        "land2_step": land2_step,
        "land3_step": land3_step,
        "first_cow_step": first_cow_step,
        "turning_point": turning_point,
        "telemetry": step_telemetry,
    }

def main():
    mp.freeze_support()
    print("=" * 120)
    print("EXP173: 10K MIDDLE-GAME (DAYS 6-15 / STEPS 120-360) CAUSAL ACTION & STATE DIVERGENCE MINE")
    print("=" * 120)

    num_workers = min(10, mp.cpu_count() or 4)
    # 100 seeds x 7 archetypes x 2 seats = 1,400 matches for high-density Phase 1 mining
    num_seeds = 100
    seeds = list(range(91001, 91001 + num_seeds))
    opp_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())
    seats = [0, 1]

    tasks = [(s, opp, seat) for s in seeds for opp in opp_keys for seat in seats]
    total_matches = len(tasks)

    print(f"Hardware Allocation : {num_workers} parallel workers on 12-core CPU")
    print(f"Evaluation Scope    : {num_seeds} Seeds x {len(opp_keys)} Opponents x 2 Seats = {total_matches} High-Resolution Matches")
    print(f"Analysis Window     : Days 6 to 15 (Steps 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360)")
    print("-" * 120)

    t0 = time.time()
    results = []
    with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
        completed = 0
        for res in pool.imap_unordered(run_trajectory_mine, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - t0
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_matches) * 100.0
            eta = (total_matches - completed) / max(0.01, rate)
            print(f"  [Progress] Completed {completed:4d}/{total_matches} ({pct:5.1f}%) | Speed: {rate:4.1f} m/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    elapsed = time.time() - t0
    print(f"\nCompleted {total_matches} simulations in {elapsed:.1f}s ({(total_matches/elapsed):.2f} matches/sec).\n")

    wins = [r for r in results if r["hero_won"]]
    losses = [r for r in results if not r["hero_won"]]
    wr = len(wins) / total_matches * 100.0

    print("=" * 120)
    print(f"OVERALL MINING POPULATION PERFORMANCE: {len(wins)}/{total_matches} Wins ({wr:.1f}%) | {len(losses)} Losses")
    print("=" * 120)

    # 1. Macro Milestone Timing Divergence (Wins vs Losses)
    print("\n" + "=" * 120)
    print("MIDDLE-GAME MILESTONE TIMING: WINS vs LOSSES")
    print("=" * 120)
    print(f"{'Milestone':<30} | {'Wins Mean Step (Day)':<24} | {'Losses Mean Step (Day)':<24} | {'Timing Delta'}")
    print("-" * 120)

    for milestone, key in [
        ("Land #2 Purchase (NE)", "land2_step"),
        ("Land #3 Purchase (SW)", "land3_step"),
        ("First Cow Acquired", "first_cow_step"),
    ]:
        w_steps = [r[key] for r in wins if r[key] is not None]
        l_steps = [r[key] for r in losses if r[key] is not None]
        w_mean = sum(w_steps) / len(w_steps) if w_steps else 0
        l_mean = sum(l_steps) / len(l_steps) if l_steps else 0
        w_day = w_mean / 24.0
        l_day = l_mean / 24.0
        delta_steps = l_mean - w_mean
        print(f"{milestone:<30} | Step {w_mean:5.1f} (Day {w_day:4.1f})   | Step {l_mean:5.1f} (Day {l_day:4.1f})   | {delta_steps:+6.1f} steps ({'SLOWER in losses' if delta_steps > 0 else 'FASTER in losses'})")
    print("=" * 120)

    # 2. Step-by-Step State Divergence (Steps 120 to 360)
    eval_steps = [120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360]
    print("\n" + "=" * 120)
    print("STEP-BY-STEP STATE TRAJECTORY DIVERGENCE (Days 6-15):")
    print("=" * 120)
    print(f"{'Step (Day)':<14} | {'Win Wealth Gap':<16} | {'Loss Wealth Gap':<16} | {'Win Cash':<14} | {'Loss Cash':<14} | {'Win Shed Straw':<16} | {'Loss Shed Straw':<16}")
    print("-" * 120)

    for s in eval_steps:
        step_k = f"Step_{s}"
        w_gaps = [r["telemetry"].get(step_k, {}).get("wealth_gap", 0) for r in wins if step_k in r["telemetry"]]
        l_gaps = [r["telemetry"].get(step_k, {}).get("wealth_gap", 0) for r in losses if step_k in r["telemetry"]]

        w_cash = [r["telemetry"].get(step_k, {}).get("hero_cash", 0) for r in wins if step_k in r["telemetry"]]
        l_cash = [r["telemetry"].get(step_k, {}).get("hero_cash", 0) for r in losses if step_k in r["telemetry"]]

        w_shed = [r["telemetry"].get(step_k, {}).get("hero_shed_straw", 0) for r in wins if step_k in r["telemetry"]]
        l_shed = [r["telemetry"].get(step_k, {}).get("hero_shed_straw", 0) for r in losses if step_k in r["telemetry"]]

        w_gap_m = sum(w_gaps) / len(w_gaps) if w_gaps else 0
        l_gap_m = sum(l_gaps) / len(l_gaps) if l_gaps else 0
        w_cash_m = sum(w_cash) / len(w_cash) if w_cash else 0
        l_cash_m = sum(l_cash) / len(l_cash) if l_cash else 0
        w_shed_m = sum(w_shed) / len(w_shed) if w_shed else 0
        l_shed_m = sum(l_shed) / len(l_shed) if l_shed else 0

        day = s // 24
        print(f"Step {s:3d} (D{day:2d})  | ${w_gap_m:+10,.1f}     | ${l_gap_m:+10,.1f}     | ${w_cash_m:10,.1f} | ${l_cash_m:10,.1f} | {w_shed_m:6.1f} units       | {l_shed_m:6.1f} units")
    print("=" * 120)

    # 3. Turning Point Distribution for Losses
    print("\n" + "=" * 120)
    print("LOSS TURNING POINT LOCALIZATION (Where Lead First Became Irreversibly Negative):")
    print("=" * 120)
    tp_counts = {}
    for r in losses:
        tp = r["turning_point"]
        tp_counts[tp] = tp_counts.get(tp, 0) + 1

    for tp, cnt in sorted(tp_counts.items(), key=lambda x: x[1], reverse=True):
        pct = cnt / len(losses) * 100.0 if losses else 0
        print(f"  {tp:<24} : {cnt:3d} losses ({pct:5.1f}%) {'█' * int(pct/5)}")
    print("=" * 120)

    # Save full dataset
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(BASE_DIR, "reports", "exp173_middle_game_causal_dataset.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Full EXP173 Middle-Game Causal Dataset to: {report_path}")

if __name__ == "__main__":
    main()
