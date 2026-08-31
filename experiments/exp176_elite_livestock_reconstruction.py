"""EXP176: Elite 8-Cow + 6-Sheep Compound Engine Counterfactual Reconstruction.

Tests whether the 8-Cow + 6-Sheep livestock compound engine observed in Grandmaster replays
is causally superior to the strawberry-centric D.1 candidate or an observational artifact.
"""
from __future__ import annotations
import os
import sys
import json
import time
import math
import multiprocessing as mp
from collections import defaultdict
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

def make_arm_agent(base_fn, arm_mode: str):
    """Constructs the policy arm agent with precise livestock expansion rules."""
    def agent(obs, conf=None):
        step = obs.get("step", 0)
        day = step // 24
        p_idx = obs.get("player", 0)
        farms = obs.get("farms", [{}, {}])
        f = farms[p_idx] if p_idx < len(farms) else {}
        money = float(f.get("money", 0.0))
        unlocked = f.get("unlocked_quadrants", ["NW"])

        # Count current animals
        cows = 0
        sheep = 0
        for row in f.get("tiles", []):
            for t in row:
                if isinstance(t, dict) and "animal" in t:
                    if t.get("animal") == "COW": cows += 1
                    elif t.get("animal") == "SHEEP": sheep += 1

        # Base candidate action
        act = _call_agent(base_fn, obs, conf)
        m = list(act.get("market", []))

        if arm_mode == "arm_a_control":
            pass

        elif arm_mode == "arm_b_early_cow":
            # Early cow on Day 0 (Step 1-4) if we have enough cash
            if step <= 4 and cows == 0 and money >= 800.0:
                if not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW" for o in m):
                    m.append(["BUY_ANIMAL", "COW", 1])

        elif arm_mode == "arm_c_early_cow_sheep":
            # 1 Cow + 1 Sheep on Day 0
            if step <= 4 and cows == 0 and money >= 800.0:
                if not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW" for o in m):
                    m.append(["BUY_ANIMAL", "COW", 1])
            elif 5 <= step <= 12 and sheep == 0 and money >= 600.0:
                if not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "SHEEP" for o in m):
                    m.append(["BUY_ANIMAL", "SHEEP", 1])

        elif arm_mode == "arm_d1_4c_2s":
            # Progressive scaling to 4 Cows + 2 Sheep
            if step <= 4 and cows == 0 and money >= 800.0:
                m.append(["BUY_ANIMAL", "COW", 1])
            elif 5 <= step <= 12 and sheep == 0 and money >= 600.0:
                m.append(["BUY_ANIMAL", "SHEEP", 1])
            elif len(unlocked) >= 3 and money >= 1200.0:
                if cows < 4 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW" for o in m):
                    m.append(["BUY_ANIMAL", "COW", min(2, 4 - cows)])
                elif sheep < 2 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "SHEEP" for o in m):
                    m.append(["BUY_ANIMAL", "SHEEP", min(1, 2 - sheep)])

        elif arm_mode == "arm_d2_6c_4s":
            # Progressive scaling to 6 Cows + 4 Sheep
            if step <= 4 and cows == 0 and money >= 800.0:
                m.append(["BUY_ANIMAL", "COW", 1])
            elif 5 <= step <= 12 and sheep == 0 and money >= 600.0:
                m.append(["BUY_ANIMAL", "SHEEP", 1])
            elif len(unlocked) >= 3 and money >= 1500.0:
                if cows < 6 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW" for o in m):
                    m.append(["BUY_ANIMAL", "COW", min(2, 6 - cows)])
                elif sheep < 4 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "SHEEP" for o in m):
                    m.append(["BUY_ANIMAL", "SHEEP", min(2, 4 - sheep)])

        elif arm_mode == "arm_e_elite_8c_6s":
            # Exact Grandmaster 8 Cows + 6 Sheep architecture
            if step <= 4 and cows < 2 and money >= 1200.0:
                m.append(["BUY_ANIMAL", "COW", 2 - cows])
            elif 5 <= step <= 12 and sheep < 2 and money >= 800.0:
                m.append(["BUY_ANIMAL", "SHEEP", 2 - sheep])
            elif len(unlocked) >= 3 and money >= 1500.0:
                if cows < 8 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW" for o in m):
                    m.append(["BUY_ANIMAL", "COW", min(2, 8 - cows)])
                elif sheep < 6 and not any(len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "SHEEP" for o in m):
                    m.append(["BUY_ANIMAL", "SHEEP", min(2, 6 - sheep)])

        # Enforce 3-quadrant ceiling
        final_orders = []
        for o in m:
            if isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(o)
        act["market"] = final_orders
        return act
    return agent

def run_arm_match(task: tuple) -> dict:
    seed, opp_key, seat, arm_name, arm_mode = task
    global _WORKER_ENV, _WORKER_CAND_AGENT, _WORKER_OPP_AGENTS
    env = _WORKER_ENV
    hero_fn = make_arm_agent(_WORKER_CAND_AGENT, arm_mode)
    opp_fn = _WORKER_OPP_AGENTS[opp_key]

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    # Track checkpoints at Day 5, 7, 10, 15, 20, 25, 29, 30
    checkpoints = [120, 168, 240, 360, 480, 600, 696]
    cash_checkpoints = {}

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        o0, o1 = env.state[0].observation, env.state[1].observation

        if step in checkpoints:
            o_hero = o0 if seat == 0 else o1
            f_hero = (o_hero.get("farms") or [{}, {}])[seat]
            cash_checkpoints[f"Day_{step//24}"] = float(f_hero.get("money", 0.0))

        if seat == 0:
            a0 = _call_agent(hero_fn, o0, env.configuration)
            a1 = _call_agent(opp_fn, o1, env.configuration)
        else:
            a0 = _call_agent(opp_fn, o0, env.configuration)
            a1 = _call_agent(hero_fn, o1, env.configuration)

        env.step([a0, a1])

    r_hero = float(env.state[seat].reward or 0)
    r_opp = float(env.state[1 - seat].reward or 0)
    hero_won = r_hero > r_opp
    margin = r_hero - r_opp

    return {
        "seed": seed,
        "opp_key": opp_key,
        "seat": seat,
        "arm_name": arm_name,
        "arm_mode": arm_mode,
        "hero_reward": r_hero,
        "opp_reward": r_opp,
        "margin": margin,
        "hero_won": hero_won,
        "cash_checkpoints": cash_checkpoints,
    }

def main():
    mp.freeze_support()
    print("=" * 120)
    print("EXP176: ELITE 8-COW + 6-SHEEP COMPOUND ENGINE COUNTERFACTUAL RECONSTRUCTION")
    print("=" * 120)

    arms = [
        ("Arm A: Control Candidate (Locked)", "arm_a_control"),
        ("Arm B: Early-Cow (Day 0 Cow)", "arm_b_early_cow"),
        ("Arm C: Early Cow + Sheep (Day 0 C+S)", "arm_c_early_cow_sheep"),
        ("Arm D1: Progressive 4C + 2S", "arm_d1_4c_2s"),
        ("Arm D2: Progressive 6C + 4S", "arm_d2_6c_4s"),
        ("Arm E: Elite 8C + 6S Grandmaster", "arm_e_elite_8c_6s"),
    ]

    num_workers = min(10, mp.cpu_count() or 4)
    # 10 seeds x 7 archetypes x 2 seats = 140 matches per arm (840 matches total)
    seeds = list(range(91001, 91011))
    opp_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())
    seats = [0, 1]

    tasks = []
    for arm_name, mode in arms:
        for s in seeds:
            for opp in opp_keys:
                for seat in seats:
                    tasks.append((s, opp, seat, arm_name, mode))

    total_tasks = len(tasks)
    print(f"Hardware: {num_workers} CPU workers | Scope: {len(arms)} Arms x {len(seeds)} Seeds x {len(opp_keys)} Opps x 2 Seats = {total_tasks} Matches")
    print("-" * 120)

    t0 = time.time()
    results = []
    with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
        completed = 0
        for res in pool.imap_unordered(run_arm_match, tasks, chunksize=1):
            results.append(res)
            completed += 1
            elapsed = time.time() - t0
            rate = completed / max(0.01, elapsed)
            pct = (completed / total_tasks) * 100.0
            eta = (total_tasks - completed) / max(0.01, rate)
            print(f"  [Progress] Completed {completed:4d}/{total_tasks} ({pct:5.1f}%) | Speed: {rate:4.1f} m/s | Elapsed: {elapsed:4.1f}s | ETA: {eta:4.1f}s", end="\r", flush=True)

    print()
    elapsed = time.time() - t0
    print(f"\nCompleted {total_tasks} counterfactual evaluations in {elapsed:.1f}s ({(total_tasks/elapsed):.2f} matches/sec).\n")

    # Group by Arm
    arm_data = {}
    for r in results:
        a = r["arm_name"]
        if a not in arm_data:
            arm_data[a] = {"wins": 0, "total": 0, "rewards": [], "margins": [], "non_mirror_wins": 0, "non_mirror_total": 0, "mirror_wins": 0, "mirror_total": 0, "cash_cp": defaultdict(list)}
        arm_data[a]["total"] += 1
        arm_data[a]["rewards"].append(r["hero_reward"])
        arm_data[a]["margins"].append(r["margin"])
        if r["hero_won"]: arm_data[a]["wins"] += 1

        is_mirror = (r["opp_key"] == "T1_v18_mirror")
        if is_mirror:
            arm_data[a]["mirror_total"] += 1
            if r["hero_won"]: arm_data[a]["mirror_wins"] += 1
        else:
            arm_data[a]["non_mirror_total"] += 1
            if r["hero_won"]: arm_data[a]["non_mirror_wins"] += 1

        for k, v in r["cash_checkpoints"].items():
            arm_data[a]["cash_cp"][k].append(v)

    ctrl_mean_rew = sum(arm_data["Arm A: Control Candidate (Locked)"]["rewards"]) / arm_data["Arm A: Control Candidate (Locked)"]["total"]

    print("=" * 120)
    print("EXP176 RESULTS: ELITE 8-COW + 6-SHEEP LIVESTOCK RECONSTRUCTION")
    print("=" * 120)
    print(f"{'Policy Arm':<36} | {'Overall WR':<14} | {'Non-Mirror WR':<16} | {'Mirror WR':<14} | {'Mean Reward':<14} | {'Delta vs Control'}")
    print("-" * 120)

    for arm_name, _ in arms:
        d = arm_data[arm_name]
        wr = (d["wins"] / d["total"]) * 100.0
        nm_wr = (d["non_mirror_wins"] / max(1, d["non_mirror_total"])) * 100.0
        m_wr = (d["mirror_wins"] / max(1, d["mirror_total"])) * 100.0
        mean_r = sum(d["rewards"]) / d["total"]
        delta_r = mean_r - ctrl_mean_rew
        print(f"{arm_name:<36} | {d['wins']:3d}/{d['total']:3d} ({wr:5.1f}%) | {d['non_mirror_wins']:3d}/{d['non_mirror_total']:3d} ({nm_wr:5.1f}%) | {d['mirror_wins']:2d}/{d['mirror_total']:2d} ({m_wr:5.1f}%) | ${mean_r:10,.1f} | ${delta_r:+10,.1f}")
    print("=" * 120)

    # Cashflow Trajectory across Days
    print("\n" + "=" * 120)
    print("LIQUID CASH RUNWAY COMPARISON ACROSS GAME PHASES (Mean Hero Money):")
    print("=" * 120)
    print(f"{'Game Phase':<18} | {'Arm A (Control)':<18} | {'Arm B (Early Cow)':<18} | {'Arm C (Early C+S)':<18} | {'Arm E (Elite 8C+6S)'}")
    print("-" * 120)
    for day_label in ["Day_5", "Day_7", "Day_10", "Day_15", "Day_20", "Day_25", "Day_29"]:
        cA = sum(arm_data["Arm A: Control Candidate (Locked)"]["cash_cp"][day_label]) / len(seeds * 14)
        cB = sum(arm_data["Arm B: Early-Cow (Day 0 Cow)"]["cash_cp"][day_label]) / len(seeds * 14)
        cC = sum(arm_data["Arm C: Early Cow + Sheep (Day 0 C+S)"]["cash_cp"][day_label]) / len(seeds * 14)
        cE = sum(arm_data["Arm E: Elite 8C + 6S Grandmaster"]["cash_cp"][day_label]) / len(seeds * 14)
        print(f"{day_label:<18} | ${cA:12,.1f}     | ${cB:12,.1f}     | ${cC:12,.1f}     | ${cE:12,.1f}")
    print("=" * 120)

    # Save full dataset
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    out_file = os.path.join(BASE_DIR, "reports", "exp176_elite_livestock_reconstruction.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Full EXP176 Reconstruction Dataset to: {out_file}")

if __name__ == "__main__":
    main()
