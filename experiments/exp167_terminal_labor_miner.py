"""EXP167 Stage 2: Fast Parallel Corrected Terminal-Labor EV Miner across Live Population."""
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
from benchmark.live_calibrated_suite import LIVE_CALIBRATED_DISTRIBUTION

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

N_SWEEPS = list(range(11))  # 0 through 10
FIB_CUMULATIVE = [0, 1, 2, 4, 7, 12, 20, 33, 54, 88, 143]

def run_step696_labor_sweep(seed: int, seat: int, b_key: str):
    entry = LIVE_CALIBRATED_DISTRIBUTION[b_key]
    opp_fn = entry["agent"]

    # 1. Play up to Step 695 and record history
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    actions_history = []
    while env.state[0].observation.get("step", 0) <= 695 and not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        actions_history.append((a0, a1))
        env.step([a0, a1] if seat == 0 else [a1, a0])

    # Extract Step 696 state
    obs0_696 = env.state[0].observation if seat == 0 else env.state[1].observation
    f0_696 = obs0_696.get("farms", [{}, {}])[0]
    p0_696 = obs0_696.get("private", {}) or {}
    mkt_696 = obs0_696.get("market", {}) or {}
    prices_696 = mkt_696.get("prices", {}) or {}

    c0_696 = float(f0_696.get("money", 0))

    # Count ripe strawberry tiles & total unharvested tiles
    straw_tiles = 0
    total_ripe_tiles = 0
    for row in f0_696.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                crop = t.get("crop")
                if crop == "STRAWBERRY": straw_tiles += 1
                if t.get("yield_units", 0) > 0: total_ripe_tiles += 1

    n_results = {}
    for n in N_SWEEPS:
        branch_env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        branch_env.reset()
        for a0_hist, a1_hist in actions_history:
            branch_env.step([a0_hist, a1_hist] if seat == 0 else [a1_hist, a0_hist])

        # Step 696: Apply N hires
        obs0_br = branch_env.state[0].observation if seat == 0 else branch_env.state[1].observation
        obs1_br = branch_env.state[1].observation if seat == 0 else branch_env.state[0].observation
        
        # Base agent action at step 696
        act0 = sub_d1._base_agent(obs0_br)
        if isinstance(act0, dict):
            m = act0.get("market", []) or []
            # Remove any existing HIRE orders
            m_filtered = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")]
            for _ in range(n):
                m_filtered.append(["HIRE"])
            act0["market"] = m_filtered[:10]

        try: act1 = opp_fn(obs1_br, branch_env.configuration)
        except TypeError: act1 = opp_fn(obs1_br)

        branch_env.step([act0, act1] if seat == 0 else [act1, act0])

        # Complete Day 29 (Steps 697 to 720) with standard base agent
        while not branch_env.done:
            o0 = branch_env.state[0].observation if seat == 0 else branch_env.state[1].observation
            o1 = branch_env.state[1].observation if seat == 0 else branch_env.state[0].observation
            a0_rem = sub_d1._base_agent(o0)
            try: a1_rem = opp_fn(o1, branch_env.configuration)
            except TypeError: a1_rem = opp_fn(o1)
            branch_env.step([a0_rem, a1_rem] if seat == 0 else [a1_rem, a0_rem])

        r0 = float(branch_env.state[seat].reward or 0.0)
        r1 = float(branch_env.state[1 - seat].reward or 0.0)
        n_results[str(n)] = {
            "hero_reward": r0,
            "opp_reward": r1,
            "margin": r0 - r1,
            "won": r0 > r1,
            "labor_cost": FIB_CUMULATIVE[n],
            "day29_rev": r0 - c0_696 + FIB_CUMULATIVE[n],
        }

    best_n = max(N_SWEEPS, key=lambda n: n_results[str(n)]["hero_reward"])
    baseline_reward = n_results["0"]["hero_reward"]
    net_ev = n_results[str(best_n)]["hero_reward"] - baseline_reward

    return {
        "bot_key": b_key,
        "cluster_name": entry["cluster_name"],
        "elo_band": entry["elo_band"],
        "seed": seed,
        "seat": seat,
        "step696_cash": c0_696,
        "straw_tiles": straw_tiles,
        "total_ripe_tiles": total_ripe_tiles,
        "best_n": best_n,
        "net_ev": float(net_ev),
        "baseline_won": n_results["0"]["won"],
        "best_n_won": n_results[str(best_n)]["won"],
        "sweeps": n_results,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        bot_keys = sys.argv[2].split(",")
        worker_id = sys.argv[3]
        seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321]
        results = []
        for b_key in bot_keys:
            if b_key not in LIVE_CALIBRATED_DISTRIBUTION: continue
            for i, seed in enumerate(seeds):
                seat = 0 if i < 5 else 1
                res = run_step696_labor_sweep(seed, seat, b_key)
                results.append(res)
        out_file = os.path.join(REPORTS_DIR, f"exp167_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    print("=" * 145)
    print("EXP167: FAST PARALLEL CORRECTED TERMINAL-LABOR EV MINER (LIVE-CALIBRATED POPULATION)")
    print("=" * 145)

    all_keys = list(LIVE_CALIBRATED_DISTRIBUTION.keys())
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.abspath(__file__), "--worker", chunk_str, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, chunk, worker_id))
        print(f"  Launched Fast Labor Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f}s. Aggregating multi-N sweep results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp167_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # Aggregate by cluster
    clusters = {}
    for d in all_data:
        c_name = d["cluster_name"]
        if c_name not in clusters: clusters[c_name] = []
        clusters[c_name].append(d)

    print("\n" + "=" * 145)
    print(f"{'Behavioral Cluster':<32} | {'Optimal N* Distribution':<30} | {'Mean Net EV over N=0 ($)':<25} | {'Baseline WR':<15} | {'Optimal N* WR'}")
    print("-" * 145)

    for c_name, items in clusters.items():
        n_stars = [x["best_n"] for x in items]
        mean_ev = np.mean([x["net_ev"] for x in items])
        base_wins = sum(1 for x in items if x["baseline_won"])
        opt_wins = sum(1 for x in items if x["best_n_won"])
        
        counts = {n: n_stars.count(n) for n in set(n_stars)}
        counts_str = ", ".join(f"N={k}:{v}" for k, v in sorted(counts.items()))
        
        base_wr_str = f"{base_wins}/{len(items)} ({base_wins/len(items)*100:.1f}%)"
        opt_wr_str = f"{opt_wins}/{len(items)} ({opt_wins/len(items)*100:.1f}%)"
        print(f"{c_name:<32} | {counts_str:<30} | ${mean_ev:+21,.2f}   | {base_wr_str:<15} | {opt_wr_str}")

    # Mirror Specific Deep-Dive
    print("\n" + "=" * 145)
    print("STRAWBERRY DUOPOLY CLONES DEEP DIVE (10 SEEDS):")
    print(f"{'Seed':<6} | {'Seat':<5} | {'N=0 Margin':<14} | {'N=10 Margin':<14} | {'Net EV ($)':<14} | {'N=0 Result':<12} | {'N=10 Result'}")
    print("-" * 145)
    mirror_items = [d for d in all_data if d["bot_key"] == "T1_v18_mirror"]
    for m in mirror_items:
        m0 = m["sweeps"]["0"]["margin"]
        m10 = m["sweeps"]["10"]["margin"]
        ev = m10 - m0
        res0 = "WIN 🏆" if m["sweeps"]["0"]["won"] else "LOSS ❌"
        res10 = "WIN 🏆" if m["sweeps"]["10"]["won"] else "LOSS ❌"
        print(f"{m['seed']:<6} | {m['seat']:<5} | ${m0:+10,.2f}   | ${m10:+10,.2f}   | ${ev:+10,.2f}   | {res0:<12} | {res10}")

    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp167_terminal_labor_miner_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"Saved Complete EXP167 Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
