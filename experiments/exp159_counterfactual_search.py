"""EXP159: Counterfactual Action Search Engine across V18 Mirror Losses."""
from __future__ import annotations
import os
import sys
import json
import copy
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

# 19 Mirror Loss Seeds from EXP149/158
MIRROR_LOSS_SEEDS = [
    1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
    20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080
]

def evaluate_counterfactual_branch(seed: int, seat: int, branch_step: int, branch_action_fn):
    """
    Runs match up to branch_step using D.1.
    At branch_step, applies branch_action_fn.
    After branch_step, continues using D.1 until step 720.
    Returns terminal rewards and W/L.
    """
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        if step == branch_step:
            a0 = branch_action_fn(obs0, env.configuration)
        else:
            a0 = sub_d1.agent(obs0, env.configuration)

        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return {"hero": r0, "opp": r1, "margin": r0 - r1, "won": r0 > r1}

def search_seed_counterfactuals(seed: int, seat: int):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    # 1. Baseline D.1 run
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

    branches = []

    # 2. Branch Set 1: Pre-terminal Cow/Milk Monetization (Steps 240, 288, 360, 480, 600)
    # Test immediate Milk & Strawberry liquidation vs D.1 order queue
    for test_step in [240, 288, 360, 480, 600, 648, 672]:
        def make_flush_action(step_val):
            def branch_fn(obs, config=None):
                act = sub_d1.agent(obs, config)
                if isinstance(act, dict):
                    f = obs.get("farms", [{}, {}])[0]
                    shed = f.get("inventory", {}) or {}
                    mkt = []
                    for k, v in shed.items():
                        if int(v) > 0: mkt.append(["SELL", k, int(v)])
                    if mkt:
                        act["market"] = mkt[:10]
                return act
            return branch_fn

        res = evaluate_counterfactual_branch(seed, seat, test_step, make_flush_action(test_step))
        delta_margin = res["margin"] - base_margin
        branches.append({
            "name": f"Flush_Inventory_Step_{test_step}",
            "step": test_step,
            "reward": res["hero"], "opp": res["opp"], "margin": res["margin"],
            "delta_vs_baseline": delta_margin, "won": res["won"]
        })

    # 3. Branch Set 2: Seed Purchase Sizing at Step 216 (Day 9)
    for delta_seeds in [-6, +6, +12]:
        def make_seed_branch(ds):
            def branch_fn(obs, config=None):
                act = sub_d1.agent(obs, config)
                if isinstance(act, dict):
                    m = act.get("market", []) or []
                    new_m = []
                    for o in m:
                        if isinstance(o, (list, tuple)) and len(o) >= 3 and o[0] == "BUY_SEED" and o[1] == "STRAWBERRY":
                            new_qty = max(1, int(o[2]) + ds)
                            new_m.append(["BUY_SEED", "STRAWBERRY", new_qty])
                        else:
                            new_m.append(o)
                    act["market"] = new_m[:10]
                return act
            return branch_fn

        res = evaluate_counterfactual_branch(seed, seat, 216, make_seed_branch(delta_seeds))
        delta_margin = res["margin"] - base_margin
        branches.append({
            "name": f"Seed_Purchase_Delta_{delta_seeds:+d}_Step_216",
            "step": 216,
            "reward": res["hero"], "opp": res["opp"], "margin": res["margin"],
            "delta_vs_baseline": delta_margin, "won": res["won"]
        })

    # 4. Branch Set 3: Step-695 / Step-696 Terminal Order Re-Prioritization
    # Counterfactual: Day 29 midnight pre-sell vs Day 30 hour 0 sell
    def make_step695_presell():
        def branch_fn(obs, config=None):
            act = sub_d1._base_agent(obs)
            if isinstance(act, dict):
                f = obs.get("farms", [{}, {}])[0]
                shed = f.get("inventory", {}) or {}
                mkt = []
                for k, v in shed.items():
                    if int(v) > 0: mkt.append(["SELL", k, int(v)])
                act["market"] = mkt[:10]
            return act
        return branch_fn

    res = evaluate_counterfactual_branch(seed, seat, 695, make_step695_presell())
    delta_margin = res["margin"] - base_margin
    branches.append({
        "name": "Pre_Sell_Flush_Step_695",
        "step": 695,
        "reward": res["hero"], "opp": res["opp"], "margin": res["margin"],
        "delta_vs_baseline": delta_margin, "won": res["won"]
    })

    # Best counterfactual branch for this seed
    best_branch = max(branches, key=lambda b: b["margin"])

    return {
        "seed": seed, "seat": seat,
        "base_reward": base_r0, "base_opp": base_r1, "base_margin": base_margin,
        "base_won": base_r0 > base_r1,
        "best_branch": best_branch,
        "all_branches": branches,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        worker_id = sys.argv[2]
        seed_idx_start = int(sys.argv[3])
        seed_idx_end = int(sys.argv[4])
        seeds_to_run = MIRROR_LOSS_SEEDS[seed_idx_start:seed_idx_end]

        results = []
        for i, seed in enumerate(seeds_to_run):
            seat = 0 if (seed_idx_start + i) < 10 else 1
            res = search_seed_counterfactuals(seed, seat)
            results.append(res)

        out_file = os.path.join(REPORTS_DIR, f"exp159_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] completed {len(results)} seeds -> {out_file}")
        return

    print("=" * 145)
    print("EXP159: COUNTERFACTUAL ACTION SEARCH ACROSS 19 V18 MIRROR LOSS TRAJECTORIES")
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
        print(f"  Launched Worker {idx} for seeds [{idx_start}:{idx_end}] (PID: {p.pid})")

    for p, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f}s. Aggregating counterfactual search results...")

    all_data = []
    for idx in range(n_workers):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp159_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Summary Scorecard of Counterfactual Conversions
    print("\n" + "=" * 145)
    print(f"{'Seed':<8} | {'Seat':<5} | {'Base Reward ($)':<16} | {'Base Margin ($)':<16} | {'Best Branch Name':<35} | {'Branch Reward ($)':<18} | {'Branch Margin ($)':<18} | {'W/L'}")
    print("-" * 145)

    conversions = 0
    margin_improvements = []

    for d in all_data:
        best_b = d["best_branch"]
        won_str = "FLIPPED TO WIN! 🏆" if (not d["base_won"] and best_b["won"]) else ("WIN" if best_b["won"] else "LOSS")
        if not d["base_won"] and best_b["won"]:
            conversions += 1
        margin_improvements.append(best_b["delta_vs_baseline"])
        print(f"{d['seed']:<8} | {d['seat']:<5} | ${d['base_reward']:12,.2f}   | ${d['base_margin']:+12,.2f}   | {best_b['name']:<35} | ${best_b['reward']:14,.2f}   | ${best_b['margin']:+14,.2f}   | {won_str}")

    print("=" * 145)
    print(f"COUNTERFACTUAL SEARCH SUMMARY (19 LOSS TRAJECTORIES):")
    print(f"  Losses Flipped to Wins: {conversions} / {len(all_data)} matches")
    print(f"  Mean Margin Delta vs Baseline: ${np.mean(margin_improvements):+,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp159_counterfactual_search_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP159 Counterfactual Search Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
