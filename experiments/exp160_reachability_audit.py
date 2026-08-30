"""EXP160: Policy Reachability & Full Action-Space Controllability Audit across 19 V18 Losses."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import importlib.util
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

MIRROR_LOSS_SEEDS = [
    1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
    20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080
]

def evaluate_reachability_branch(seed: int, seat: int, branch_step: int, branch_fn):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        if step == branch_step:
            a0 = branch_fn(obs0, env.configuration)
        else:
            a0 = sub_d1.agent(obs0, env.configuration)

        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return {"hero": r0, "opp": r1, "margin": r0 - r1, "won": r0 > r1}

def audit_seed_reachability(seed: int, seat: int):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    # 1. Baseline Run
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])

    base_r0 = float(env.state[seat].reward or 0.0)
    base_r1 = float(env.state[1 - seat].reward or 0.0)
    base_margin = base_r0 - base_r1
    base_won = base_r0 > base_r1

    branches = []

    # 2. Category 1: Land Expansion Timing (Steps 216, 240, 264, 288)
    for l_step in [216, 240, 264, 288]:
        def make_land_branch():
            def fn(obs, cfg=None):
                act = sub_d1.agent(obs, cfg)
                if isinstance(act, dict):
                    m = act.get("market", []) or []
                    m.append(["BUY_LAND"])
                    act["market"] = m[:10]
                return act
            return fn
        res = evaluate_reachability_branch(seed, seat, l_step, make_land_branch())
        branches.append({"category": "LAND_TIMING", "name": f"Buy_Land_Step_{l_step}", "step": l_step, "margin": res["margin"], "won": res["won"], "reward": res["hero"]})

    # 3. Category 2: Early Worker Injection (Steps 216, 264, 312, 360)
    for w_step in [216, 264, 312, 360]:
        for n_w in [1, 2]:
            def make_worker_branch(nw):
                def fn(obs, cfg=None):
                    act = sub_d1.agent(obs, cfg)
                    if isinstance(act, dict):
                        m = act.get("market", []) or []
                        for _ in range(nw): m.append(["HIRE"])
                        act["market"] = m[:10]
                    return act
                return fn
            res = evaluate_reachability_branch(seed, seat, w_step, make_worker_branch(n_w))
            branches.append({"category": "WORKER_INJECTION", "name": f"Hire_{n_w}_Workers_Step_{w_step}", "step": w_step, "margin": res["margin"], "won": res["won"], "reward": res["hero"]})

    # 4. Category 3: Livestock Expansion (Steps 216, 240, 264)
    for a_step in [216, 240, 264]:
        for animal_type in ["COW", "SHEEP"]:
            def make_animal_branch(atype):
                def fn(obs, cfg=None):
                    act = sub_d1.agent(obs, cfg)
                    if isinstance(act, dict):
                        m = act.get("market", []) or []
                        m.append(["BUY_ANIMAL", atype, 1])
                        act["market"] = m[:10]
                    return act
                return fn
            res = evaluate_reachability_branch(seed, seat, a_step, make_animal_branch(animal_type))
            branches.append({"category": "LIVESTOCK_EXPANSION", "name": f"Buy_{animal_type}_Step_{a_step}", "step": a_step, "margin": res["margin"], "won": res["won"], "reward": res["hero"]})

    # 5. Category 4: Commodity Liquidation Batch Sizes (Steps 312, 360, 480)
    for m_step in [312, 360, 480]:
        def make_milk_flush():
            def fn(obs, cfg=None):
                act = sub_d1.agent(obs, cfg)
                if isinstance(act, dict):
                    f = obs.get("farms", [{}, {}])[0]
                    shed = f.get("inventory", {}) or {}
                    milk = int(shed.get("MILK", 0) or 0)
                    if milk > 0:
                        m = act.get("market", []) or []
                        m.append(["SELL", "MILK", milk])
                        act["market"] = m[:10]
                return act
            return fn
        res = evaluate_reachability_branch(seed, seat, m_step, make_milk_flush())
        branches.append({"category": "MILK_LIQUIDATION", "name": f"Flush_Milk_Step_{m_step}", "step": m_step, "margin": res["margin"], "won": res["won"], "reward": res["hero"]})

    # Find if ANY branch achieves a win
    winning_branches = [b for b in branches if b["won"]]
    best_branch = max(branches, key=lambda b: b["margin"])

    return {
        "seed": seed, "seat": seat,
        "base_reward": base_r0, "base_opp": base_r1, "base_margin": base_margin,
        "base_won": base_won,
        "win_reachable": len(winning_branches) > 0,
        "num_winning_branches": len(winning_branches),
        "best_branch": best_branch,
        "winning_branches": winning_branches,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        worker_id = sys.argv[2]
        idx_start = int(sys.argv[3])
        idx_end = int(sys.argv[4])
        seeds_to_run = MIRROR_LOSS_SEEDS[idx_start:idx_end]

        results = []
        for i, seed in enumerate(seeds_to_run):
            seat = 0 if (idx_start + i) < 10 else 1
            res = audit_seed_reachability(seed, seat)
            results.append(res)

        out_file = os.path.join(REPORTS_DIR, f"exp160_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] completed {len(results)} seeds -> {out_file}")
        return

    print("=" * 145)
    print("EXP160: FULL ACTION-SPACE POLICY REACHABILITY AUDIT (19 V18 MIRROR LOSSES)")
    print("=" * 145)

    n_workers = 4
    chunk_size = int(np.ceil(len(MIRROR_LOSS_SEEDS) / n_workers))

    processes = []
    t0 = time.time()

    for idx in range(n_workers):
        worker_id = f"worker_{idx}"
        idx_start = idx * chunk_size
        idx_end = min(len(MIRROR_LOSS_SEEDS), (idx + 1) * chunk_size)
        if idx_start >= len(MIRROR_LOSS_SEEDS): break

        cmd = [sys.executable, os.path.abspath(__file__), "--worker", worker_id, str(idx_start), str(idx_end)]
        p = subprocess.Popen(cmd)
        processes.append((p, worker_id))
        print(f"  Launched Reachability Worker {idx} for seeds [{idx_start}:{idx_end}] (PID: {p.pid})")

    for p, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating reachability space...")

    all_data = []
    for idx in range(n_workers):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp160_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Summary Scorecard of Policy Reachability
    print("\n" + "=" * 145)
    print(f"{'Seed':<8} | {'Seat':<5} | {'Base Reward ($)':<16} | {'Base Margin ($)':<16} | {'Win Reachable?':<16} | {'Best Branch Category':<24} | {'Best Branch Margin ($)'}")
    print("-" * 145)

    reachable_count = 0
    for d in all_data:
        reach_str = "YES 🏆" if d["win_reachable"] else "NO ❌ (Unreachable)"
        if d["win_reachable"]: reachable_count += 1
        best_b = d["best_branch"]
        print(f"{d['seed']:<8} | {d['seat']:<5} | ${d['base_reward']:12,.2f}   | ${d['base_margin']:+12,.2f}   | {reach_str:<16} | {best_b['category']:<24} | ${best_b['margin']:+18,.2f}")

    print("=" * 145)
    print(f"POLICY REACHABILITY VERDICT (19 V18 LOSSES):")
    print(f"  Matches with Reachable Win Action : {reachable_count} / {len(all_data)} ({reachable_count/len(all_data)*100:.1f}%)")
    print(f"  Matches Structurally Unreachable  : {len(all_data) - reachable_count} / {len(all_data)} ({(len(all_data)-reachable_count)/len(all_data)*100:.1f}%)")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp160_reachability_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP160 Policy Reachability Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
