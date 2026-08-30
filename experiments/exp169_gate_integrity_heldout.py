"""EXP169: Candidate Integrity & Held-Out Generalization Audit."""
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

FIB_CUMULATIVE = [0, 1, 2, 4, 7, 12, 20, 33, 54, 88, 143]

def compute_state_dependent_n_star_detailed(farm: dict, private: dict, prices: dict):
    """
    Returns (N*, ripe_tiles, v_rec, labor_cost) with full state introspection.
    """
    tiles = farm.get("tiles", [])
    p_straw = float(prices.get("STRAWBERRY", 120))
    p_carrot = float(prices.get("CARROT", 35))
    p_milk = float(prices.get("MILK", 120))
    p_wool = float(prices.get("WOOL", 150))

    ripe_tiles = 0
    recoverable_value = 0.0

    for row in tiles:
        for t in row:
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT":
                    crop = t.get("crop")
                    y = t.get("yield_units", 0)
                    if y > 0:
                        ripe_tiles += 1
                        price = p_straw if crop == "STRAWBERRY" else (p_carrot if crop == "CARROT" else 20)
                        recoverable_value += y * price
                elif "animal" in t:
                    a = t.get("animal")
                    y = t.get("yield_units", 0)
                    if y > 0:
                        ripe_tiles += 1
                        price = p_milk if a == "COW" else p_wool
                        recoverable_value += y * price

    if ripe_tiles <= 4:
        return 0, ripe_tiles, recoverable_value, 0

    backlog = ripe_tiles - 4
    needed_hands = int(np.ceil(backlog / 2.0))
    candidate_n = min(10, max(0, needed_hands))

    cost = FIB_CUMULATIVE[candidate_n]
    if recoverable_value > cost * 2.0:
        chosen_n = candidate_n
    elif recoverable_value > FIB_CUMULATIVE[min(4, candidate_n)] * 2.0:
        chosen_n = min(4, candidate_n)
    else:
        chosen_n = 0

    return chosen_n, ripe_tiles, recoverable_value, FIB_CUMULATIVE[chosen_n]

def run_match_arm_step696(seed: int, seat: int, b_key: str, arm: str):
    entry = LIVE_CALIBRATED_DISTRIBUTION[b_key]
    opp_fn = entry["agent"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    n_hired = 0
    step696_v_rec = 0.0
    step696_ripe_tiles = 0
    step696_cash = 0.0

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        if step == 696:
            f0 = obs0.get("farms", [{}, {}])[0]
            p0 = obs0.get("private", {}) or {}
            mkt = obs0.get("market", {}) or {}
            prices = mkt.get("prices", {}) or {}
            step696_cash = float(f0.get("money", 0))

            chosen_n, ripe_t, v_rec, _ = compute_state_dependent_n_star_detailed(f0, p0, prices)
            step696_ripe_tiles = ripe_t
            step696_v_rec = v_rec

            if arm == "ArmA_D1_Control":
                n_to_hire = 0
            elif arm == "ArmB_Always_N10":
                n_to_hire = 10
            elif arm == "ArmC_Gated_NStar":
                n_to_hire = chosen_n

            n_hired = n_to_hire

            act0 = sub_d1._base_agent(obs0)
            if isinstance(act0, dict):
                m = act0.get("market", []) or []
                m_clean = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")]
                for _ in range(n_to_hire):
                    m_clean.append(["HIRE"])
                act0["market"] = m_clean[:10]
        elif step > 696:
            act0 = sub_d1._base_agent(obs0)
        else:
            act0 = sub_d1.agent(obs0, env.configuration)

        try: act1 = opp_fn(obs1, env.configuration)
        except TypeError: act1 = opp_fn(obs1)

        env.step([act0, act1] if seat == 0 else [act1, act0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    day29_rev = (r0 - step696_cash) + FIB_CUMULATIVE[n_hired]

    return {
        "bot_key": b_key,
        "cluster_name": entry["cluster_name"],
        "elo_band": entry["elo_band"],
        "seed": seed,
        "seat": seat,
        "arm": arm,
        "n_hired": n_hired,
        "labor_cost": FIB_CUMULATIVE[n_hired],
        "step696_v_rec": step696_v_rec,
        "step696_ripe_tiles": step696_ripe_tiles,
        "step696_cash": step696_cash,
        "day29_gross_rev": day29_rev,
        "hero_reward": r0,
        "opp_reward": r1,
        "margin": r0 - r1,
        "won": r0 > r1,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        bot_keys = sys.argv[2].split(",")
        worker_id = sys.argv[3]
        # Held-out 20 seeds (Seed 80001 to 80020)
        seeds = [80001 + i * 7 for i in range(20)]
        results = []
        for b_key in bot_keys:
            if b_key not in LIVE_CALIBRATED_DISTRIBUTION: continue
            for i, seed in enumerate(seeds):
                seat = 0 if i < 10 else 1
                res_a = run_match_arm_step696(seed, seat, b_key, "ArmA_D1_Control")
                res_b = run_match_arm_step696(seed, seat, b_key, "ArmB_Always_N10")
                res_c = run_match_arm_step696(seed, seat, b_key, "ArmC_Gated_NStar")
                results.append({
                    "bot_key": b_key, "cluster_name": res_a["cluster_name"], "elo_band": res_a["elo_band"],
                    "seed": seed, "seat": seat,
                    "ArmA": res_a, "ArmB": res_b, "ArmC": res_c,
                })
        out_file = os.path.join(REPORTS_DIR, f"exp169_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    print("=" * 145)
    print("EXP169: CANDIDATE INTEGRITY & HELD-OUT GENERALIZATION AUDIT (280 HELD-OUT MATCH EVALUATION)")
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
        print(f"  Launched Held-Out Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f}s. Aggregating held-out validation dataset...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp169_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Gate Discrimination & Chosen N Distribution
    print("\n" + "=" * 145)
    print("GATE DISCRIMINATION & CHOSEN N* DISTRIBUTION ON HELD-OUT DATASET:")
    print(f"{'Behavioral Cluster':<30} | {'Chosen N Distribution':<30} | {'Mean V_rec ($)':<16} | {'Mean Day 29 Gross Rev':<22} | {'Mean Labor Cost ($)'}")
    print("-" * 145)

    clusters = {}
    for d in all_data:
        c_name = d["cluster_name"]
        if c_name not in clusters: clusters[c_name] = []
        clusters[c_name].append(d)

    for c_name, items in clusters.items():
        n_stars = [x["ArmC"]["n_hired"] for x in items]
        v_recs = [x["ArmC"]["step696_v_rec"] for x in items]
        revs = [x["ArmC"]["day29_gross_rev"] for x in items]
        costs = [x["ArmC"]["labor_cost"] for x in items]

        counts = {n: n_stars.count(n) for n in set(n_stars)}
        counts_str = ", ".join(f"N={k}:{v}" for k, v in sorted(counts.items()))

        print(f"{c_name:<30} | {counts_str:<30} | ${np.mean(v_recs):13,.2f} | ${np.mean(revs):19,.2f} | ${np.mean(costs):16,.2f}")

    # 2. Held-Out Generalization Performance Table
    print("\n" + "=" * 145)
    print(f"{'Behavioral Cluster':<30} | {'Held-Out Matches':<18} | {'Arm A (D.1 Control)':<22} | {'Arm B (Always N=10)':<22} | {'Arm C (Gated N*)':<22} | {'Net Conversions (C vs A)'}")
    print("-" * 145)

    total_matches = len(all_data)
    total_a_wins, total_b_wins, total_c_wins = 0, 0, 0
    total_l2w, total_w2l = 0, 0

    for c_name, items in clusters.items():
        n_m = len(items)
        a_wins = sum(1 for x in items if x["ArmA"]["won"])
        b_wins = sum(1 for x in items if x["ArmB"]["won"])
        c_wins = sum(1 for x in items if x["ArmC"]["won"])

        total_a_wins += a_wins
        total_b_wins += b_wins
        total_c_wins += c_wins

        l2w = sum(1 for x in items if not x["ArmA"]["won"] and x["ArmC"]["won"])
        w2l = sum(1 for x in items if x["ArmA"]["won"] and not x["ArmC"]["won"])
        net_conv = l2w - w2l
        total_l2w += l2w
        total_w2l += w2l

        a_str = f"{a_wins:2d}/{n_m:2d} ({a_wins/n_m*100:5.1f}%)"
        b_str = f"{b_wins:2d}/{n_m:2d} ({b_wins/n_m*100:5.1f}%)"
        c_str = f"{c_wins:2d}/{n_m:2d} ({c_wins/n_m*100:5.1f}%)"
        conv_str = f"+{l2w} L->W, -{w2l} W->L (Net: {net_conv:+2d})"

        print(f"{c_name:<30} | {n_m:<18} | {a_str:<22} | {b_str:<22} | {c_str:<22} | {conv_str}")

    print("=" * 145)
    print(f"{'HELD-OUT RAW TOTAL':<30} | {total_matches:<18} | {total_a_wins:2d}/{total_matches:2d} ({total_a_wins/total_matches*100:5.1f}%)         | {total_b_wins:2d}/{total_matches:2d} ({total_b_wins/total_matches*100:5.1f}%)         | {total_c_wins:2d}/{total_matches:2d} ({total_c_wins/total_matches*100:5.1f}%)         | +{total_l2w} L->W, -{total_w2l} W->L (Net: {total_l2w - total_w2l:+2d})")
    print("=" * 145)

    # 3. Live Population Synthesis on Fresh Held-Out Data
    weights = {
        "Strawberry_Duopoly_Clones": 0.488,
        "Price_Responsive_Hybrids": 0.240,
        "Cattle_Agro_Conglomerates": 0.155,
        "Primitive_Legacy_Rushers": 0.117,
    }

    live_wr_a = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmA"]["won"]) / len(clusters[c])) for c in clusters) * 100
    live_wr_b = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmB"]["won"]) / len(clusters[c])) for c in clusters) * 100
    live_wr_c = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmC"]["won"]) / len(clusters[c])) for c in clusters) * 100

    print("\nHELD-OUT DATASET LIVE-CALIBRATED EXPECTED WIN RATE:")
    print(f"  Arm A (Exact D.1 Control Baseline) : {live_wr_a:5.1f}% Live WR")
    print(f"  Arm B (Unconditional Always N=10)  : {live_wr_b:5.1f}% Live WR (Delta: {live_wr_b - live_wr_a:+5.1f}%)")
    print(f"  Arm C (State-Dependent Gated N*)   : {live_wr_c:5.1f}% Live WR (Delta: {live_wr_c - live_wr_a:+5.1f}%)")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp169_heldout_validation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP169 Held-Out Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
