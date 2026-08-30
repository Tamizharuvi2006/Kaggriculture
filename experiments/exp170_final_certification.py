"""EXP170: 3-Way Final Gate Certification & Standalone Deployment Audit."""
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

# Import exact Control D.1
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Import Candidate Adaptive Terminal
spec_cand = importlib.util.spec_from_file_location("sub_cand", os.path.join(BASE_DIR, "candidate_adaptive_terminal.py"))
sub_cand = importlib.util.module_from_spec(spec_cand)
spec_cand.loader.exec_module(sub_cand)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

FIB_CUMULATIVE = [0, 1, 2, 4, 7, 12, 20, 33, 54, 88, 143]

# ----------------------------------------------------------------------------------------------------
# 1. PARITY AUDIT (Steps 0 to 695)
# ----------------------------------------------------------------------------------------------------
def run_action_stream_parity_audit(seeds: list[int] = [1000, 42, 100, 200, 500]):
    print("\n" + "=" * 100)
    print("GATE 1: ACTION-STREAM PARITY AUDIT (STEPS 0 TO 695)")
    print("=" * 100)

    opp_fn = LIVE_CALIBRATED_DISTRIBUTION["T1_v18_mirror"]["agent"]
    total_steps_checked = 0
    diffs_found = 0

    for seed in seeds:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        while env.state[0].observation.get("step", 0) <= 695 and not env.done:
            obs0 = env.state[0].observation
            act_d1 = sub_d1.agent(obs0, env.configuration)
            act_cand = sub_cand.agent(obs0, env.configuration)

            if act_d1 != act_cand:
                diffs_found += 1
                print(f"  ❌ Parity Diff at Seed {seed}, Step {obs0.get('step')}: D1={act_d1} vs CAND={act_cand}")

            total_steps_checked += 1
            try: act1 = opp_fn(env.state[1].observation, env.configuration)
            except TypeError: act1 = opp_fn(env.state[1].observation)
            env.step([act_cand, act1])

    print(f"  Checked {total_steps_checked} steps across {len(seeds)} matches.")
    print(f"  Total Action Divergences (Steps 0-695): {diffs_found}")
    pass_gate1 = (diffs_found == 0)
    print(f"  VERDICT GATE 1: {'PASS ✅' if pass_gate1 else 'FAIL ❌'}")
    return pass_gate1

# ----------------------------------------------------------------------------------------------------
# 2. PHYSICAL REVENUE & FIBONACCI AUDIT
# ----------------------------------------------------------------------------------------------------
def run_physical_accounting_validation(seed: int = 1000):
    print("\n" + "=" * 100)
    print("GATE 2: PHYSICAL ACCOUNTING & INCREMENTAL REVENUE VALIDATION")
    print("=" * 100)

    opp_fn = LIVE_CALIBRATED_DISTRIBUTION["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    while env.state[0].observation.get("step", 0) <= 695 and not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        a0 = sub_cand.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env.step([a0, a1])

    obs_696 = env.state[0].observation
    f0_696 = obs_696.get("farms", [{}, {}])[0]
    cash_696 = float(f0_696.get("money", 0))

    # Candidate step 696 execution
    a0_696 = sub_cand.agent(obs_696, env.configuration)
    try: a1_696 = opp_fn(env.state[1].observation, env.configuration)
    except TypeError: a1_696 = opp_fn(env.state[1].observation)
    env.step([a0_696, a1_696])

    obs_697 = env.state[0].observation
    f0_697 = obs_697.get("farms", [{}, {}])[0]
    cash_697 = float(f0_697.get("money", 0))
    hands_spawned = len(f0_697.get("hands", []))
    actual_cost = cash_696 - cash_697

    # Finish match
    while not env.done:
        o0 = env.state[0].observation
        o1 = env.state[1].observation
        a0_rem = sub_cand.agent(o0, env.configuration)
        try: a1_rem = opp_fn(o1, env.configuration)
        except TypeError: a1_rem = opp_fn(o1)
        env.step([a0_rem, a1_rem])

    final_reward = float(env.state[0].reward or 0)
    day29_gross_rev = (final_reward - cash_696) + actual_cost

    print(f"  Step 696 Initial Cash : ${cash_696:,.2f}")
    print(f"  Hands Spawned at 696  : {hands_spawned}")
    print(f"  Actual Deducted Cost  : ${actual_cost:.2f} (Expected for {hands_spawned} hires: ${FIB_CUMULATIVE[hands_spawned]:.2f})")
    print(f"  Final Match Reward    : ${final_reward:,.2f}")
    print(f"  Day 29 Gross Sales    : ${day29_gross_rev:,.2f}")
    print(f"  Day 29 Net Profit     : ${day29_gross_rev - actual_cost:,.2f}")

    pass_cost = (actual_cost == FIB_CUMULATIVE[hands_spawned])
    pass_hands = (hands_spawned == 10)
    pass_profit = (day29_gross_rev > actual_cost * 10)
    pass_gate2 = pass_cost and pass_hands and pass_profit
    print(f"  VERDICT GATE 2: {'PASS ✅' if pass_gate2 else 'FAIL ❌'}")
    return pass_gate2

# ----------------------------------------------------------------------------------------------------
# 3. FRESH HELD-OUT 3-WAY COMPARATIVE BENCHMARK (Seeds 90001..90140)
# ----------------------------------------------------------------------------------------------------
def run_match_arm_exp170(seed: int, seat: int, b_key: str, arm: str):
    entry = LIVE_CALIBRATED_DISTRIBUTION[b_key]
    opp_fn = entry["agent"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    n_hired = 0
    step696_cash = 0.0

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        if step == 696:
            f0 = obs0.get("farms", [{}, {}])[0]
            step696_cash = float(f0.get("money", 0))

        if arm == "ArmA_D1_Control":
            act0 = sub_d1.agent(obs0, env.configuration)
        elif arm == "ArmB_Always_N10":
            if step == 696:
                act0 = sub_d1._base_agent(obs0)
                m = act0.get("market", []) or []
                m_clean = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")]
                for _ in range(10): m_clean.append(["HIRE"])
                act0["market"] = m_clean[:10]
            elif step > 696:
                act0 = sub_d1._base_agent(obs0)
            else:
                act0 = sub_d1.agent(obs0, env.configuration)
        elif arm == "ArmC_Adaptive_Candidate":
            act0 = sub_cand.agent(obs0, env.configuration)

        if step == 696 and isinstance(act0, dict):
            m = act0.get("market", []) or []
            n_hired = sum(1 for o in m if isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")

        try: act1 = opp_fn(obs1, env.configuration)
        except TypeError: act1 = opp_fn(obs1)

        env.step([act0, act1] if seat == 0 else [act1, act0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "bot_key": b_key,
        "cluster_name": entry["cluster_name"],
        "elo_band": entry["elo_band"],
        "seed": seed,
        "seat": seat,
        "arm": arm,
        "n_hired": n_hired,
        "labor_cost": FIB_CUMULATIVE[n_hired],
        "hero_reward": r0,
        "opp_reward": r1,
        "margin": r0 - r1,
        "won": r0 > r1,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        bot_keys = sys.argv[2].split(",")
        worker_id = sys.argv[3]
        # Fresh held-out seeds (90001 + i * 11)
        seeds = [90001 + i * 11 for i in range(20)]
        results = []
        for b_key in bot_keys:
            if b_key not in LIVE_CALIBRATED_DISTRIBUTION: continue
            for i, seed in enumerate(seeds):
                seat = 0 if i < 10 else 1
                res_a = run_match_arm_exp170(seed, seat, b_key, "ArmA_D1_Control")
                res_b = run_match_arm_exp170(seed, seat, b_key, "ArmB_Always_N10")
                res_c = run_match_arm_exp170(seed, seat, b_key, "ArmC_Adaptive_Candidate")
                results.append({
                    "bot_key": b_key, "cluster_name": res_a["cluster_name"], "elo_band": res_a["elo_band"],
                    "seed": seed, "seat": seat,
                    "ArmA": res_a, "ArmB": res_b, "ArmC": res_c,
                })
        out_file = os.path.join(REPORTS_DIR, f"exp170_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    print("=" * 145)
    print("EXP170: 3-WAY FINAL GATE CERTIFICATION & STANDALONE DEPLOYMENT AUDIT")
    print("=" * 145)

    gate1_pass = run_action_stream_parity_audit()
    gate2_pass = run_physical_accounting_validation()

    print("\n" + "=" * 100)
    print("GATE 3 & 4: FRESH HELD-OUT POPULATION BENCHMARK (SEEDS 90001..90220)")
    print("=" * 100)

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
        print(f"  Launched Fresh Certification Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f}s. Aggregating certification results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp170_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    clusters = {}
    for d in all_data:
        c_name = d["cluster_name"]
        if c_name not in clusters: clusters[c_name] = []
        clusters[c_name].append(d)

    total_matches = len(all_data)
    total_a_wins, total_b_wins, total_c_wins = 0, 0, 0
    total_l2w, total_w2l = 0, 0

    print("\n" + "=" * 145)
    print(f"{'Behavioral Cluster':<30} | {'Held-Out Matches':<18} | {'Arm A (D.1 Control)':<22} | {'Arm B (Always N=10)':<22} | {'Arm C (Candidate N*)':<22} | {'Net Conversions (C vs A)'}")
    print("-" * 145)

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
    print(f"{'TOTAL EVALUATED':<30} | {total_matches:<18} | {total_a_wins:2d}/{total_matches:2d} ({total_a_wins/total_matches*100:5.1f}%)         | {total_b_wins:2d}/{total_matches:2d} ({total_b_wins/total_matches*100:5.1f}%)         | {total_c_wins:2d}/{total_matches:2d} ({total_c_wins/total_matches*100:5.1f}%)         | +{total_l2w} L->W, -{total_w2l} W->L (Net: {total_l2w - total_w2l:+2d})")
    print("=" * 145)

    weights = {
        "Strawberry_Duopoly_Clones": 0.488,
        "Price_Responsive_Hybrids": 0.240,
        "Cattle_Agro_Conglomerates": 0.155,
        "Primitive_Legacy_Rushers": 0.117,
    }

    live_wr_a = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmA"]["won"]) / len(clusters[c])) for c in clusters) * 100
    live_wr_b = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmB"]["won"]) / len(clusters[c])) for c in clusters) * 100
    live_wr_c = sum(weights[c] * (sum(1 for x in clusters[c] if x["ArmC"]["won"]) / len(clusters[c])) for c in clusters) * 100

    print("\nEXP170 HELD-OUT LIVE-CALIBRATED EXPECTED WIN RATE:")
    print(f"  Arm A (Exact D.1 Baseline)         : {live_wr_a:5.1f}% Live WR")
    print(f"  Arm B (Unconditional Always N=10)  : {live_wr_b:5.1f}% Live WR (Delta: {live_wr_b - live_wr_a:+5.1f}%)")
    print(f"  Arm C (Candidate Adaptive N*)      : {live_wr_c:5.1f}% Live WR (Delta: {live_wr_c - live_wr_a:+5.1f}%)")
    print("=" * 145)

    gate3_pass = (total_l2w >= 10)
    gate4_pass = (total_w2l == 0)
    print(f"  GATE 3 (Loss->Win Conversions >= 10): {'PASS ✅' if gate3_pass else 'FAIL ❌'} (+{total_l2w})")
    print(f"  GATE 4 (Win->Loss Regressions == 0) : {'PASS ✅' if gate4_pass else 'FAIL ❌'} (-{total_w2l})")

    out_json = os.path.join(REPORTS_DIR, "exp170_certification_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved EXP170 Certification Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
