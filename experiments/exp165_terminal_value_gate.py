"""EXP165: Fast Parallel Terminal Harvest Value Gate & Multi-N Sweep Miner."""
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

N_SWEEPS = [0, 2, 4, 6, 8, 10]

def calculate_field_potential(farm: dict, private: dict, prices: dict) -> float:
    """Estimates unharvested crop value and animal yield potential on Day 30."""
    total_val = 0.0
    tiles = farm.get("tiles", [])
    p_straw = float(prices.get("STRAWBERRY", 120))
    p_milk = float(prices.get("MILK", 120))
    p_wool = float(prices.get("WOOL", 150))
    p_carrot = float(prices.get("CARROT", 35))

    for row in tiles:
        for t in row:
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT":
                    crop = t.get("crop")
                    y = t.get("yield_units", 0)
                    price = p_straw if crop == "STRAWBERRY" else (p_carrot if crop == "CARROT" else 20)
                    total_val += (y * price)
                elif "animal" in t:
                    a = t.get("animal")
                    y = t.get("yield_units", 0)
                    price = p_milk if a == "COW" else p_wool
                    total_val += (y * price)
    return total_val

def run_step696_sweep(seed: int, seat: int, b_key: str):
    entry = LIVE_CALIBRATED_DISTRIBUTION[b_key]
    opp_fn = entry["agent"]

    # 1. Run simulation up to Step 695 and save trajectory
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    actions_history = []
    while env.state[0].observation.get("step", 0) < 695 and not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        actions_history.append((a0, a1))
        env.step([a0, a1] if seat == 0 else [a1, a0])

    # 2. Extract Step-695 public state and estimate V_field
    obs0_695 = env.state[0].observation if seat == 0 else env.state[1].observation
    f0_695 = obs0_695.get("farms", [{}, {}])[0]
    priv0_695 = obs0_695.get("private", {}) or {}
    mkt_695 = obs0_695.get("market", {}) or {}
    prices_695 = mkt_695.get("prices", {}) or {}
    
    v_field = calculate_field_potential(f0_695, priv0_695, prices_695)

    # 3. Sweep N in [0, 2, 4, 6, 8, 10]
    n_results = {}
    for n in N_SWEEPS:
        # Re-create environment and replay up to 695
        branch_env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        branch_env.reset()
        for a0_hist, a1_hist in actions_history:
            branch_env.step([a0_hist, a1_hist] if seat == 0 else [a1_hist, a0_hist])

        # Step 696: Apply N hires
        obs0_br = branch_env.state[0].observation if seat == 0 else branch_env.state[1].observation
        obs1_br = branch_env.state[1].observation if seat == 0 else branch_env.state[0].observation
        
        # Use base agent or explicit N hires
        act0 = sub_d1._base_agent(obs0_br)
        if isinstance(act0, dict):
            m = act0.get("market", []) or []
            # Filter existing HIRE orders
            m_no_hire = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")]
            for _ in range(n):
                m_no_hire.append(["HIRE"])
            act0["market"] = m_no_hire[:10]

        try: act1 = opp_fn(obs1_br, branch_env.configuration)
        except TypeError: act1 = opp_fn(obs1_br)

        branch_env.step([act0, act1] if seat == 0 else [act1, act0])

        # Continue Steps 697-720 using standard base agent with harvest
        while not branch_env.done:
            o0 = branch_env.state[0].observation if seat == 0 else branch_env.state[1].observation
            o1 = branch_env.state[1].observation if seat == 0 else branch_env.state[0].observation
            a0_rem = sub_d1._base_agent(o0)
            try: a1_rem = opp_fn(o1, branch_env.configuration)
            except TypeError: a1_rem = opp_fn(o1)
            branch_env.step([a0_rem, a1_rem] if seat == 0 else [a1_rem, a0_rem])

        r0_final = float(branch_env.state[seat].reward or 0.0)
        r1_final = float(branch_env.state[1 - seat].reward or 0.0)
        n_results[str(n)] = {
            "hero_reward": r0_final,
            "opp_reward": r1_final,
            "margin": r0_final - r1_final,
            "won": r0_final > r1_final,
            "labor_cost": n * 500.0,
        }

    # Find optimal N* for this state
    best_n = max(N_SWEEPS, key=lambda n: n_results[str(n)]["hero_reward"])
    baseline_reward = n_results["0"]["hero_reward"]
    net_ev = n_results[str(best_n)]["hero_reward"] - baseline_reward

    return {
        "bot_key": b_key,
        "cluster_name": entry["cluster_name"],
        "elo_band": entry["elo_band"],
        "seed": seed,
        "seat": seat,
        "v_field_step695": float(v_field),
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
                res = run_step696_sweep(seed, seat, b_key)
                results.append(res)
        out_file = os.path.join(REPORTS_DIR, f"exp165_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    print("=" * 145)
    print("EXP165: FAST PARALLEL TERMINAL HARVEST VALUE GATE MINER (LIVE-CALIBRATED BENCHMARK)")
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
        print(f"  Launched Fast Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating multi-N sweep results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp165_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Cluster Analysis of Optimal N*
    print("\n" + "=" * 145)
    print(f"{'Behavioral Cluster':<32} | {'Mean V_field ($)':<18} | {'Optimal N* Distribution':<30} | {'Mean Net EV ($)':<18} | {'W/L Impact'}")
    print("-" * 145)

    clusters = {}
    for d in all_data:
        c_name = d["cluster_name"]
        if c_name not in clusters: clusters[c_name] = []
        clusters[c_name].append(d)

    for c_name, items in clusters.items():
        mean_vf = np.mean([x["v_field_step695"] for x in items])
        n_stars = [x["best_n"] for x in items]
        mean_ev = np.mean([x["net_ev"] for x in items])
        base_wins = sum(1 for x in items if x["baseline_won"])
        gated_wins = sum(1 for x in items if x["best_n_won"])
        
        n_dist_str = f"N=0: {n_stars.count(0)}, N=2: {n_stars.count(2)}, N=10: {n_stars.count(10)}"
        print(f"{c_name:<32} | ${mean_vf:14,.2f}   | {n_dist_str:<30} | ${mean_ev:+14,.2f}   | {base_wins}/{len(items)} -> {gated_wins}/{len(items)}")

    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp165_terminal_value_gate_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP165 Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
