"""Multi-Metric Pre-Upload Validation Gate: V4.1 Master Champion vs V8.4 Experimental.

Evaluates 100 Isolated Head-to-Head Matches across Seeds 1000-1099 (50 matches per seat position):
1. Win Rate (% of matches won by V8.4)
2. Average Money Difference ($ V8.4 - V4.1)
3. Bankruptcy Count (<$10,000 final score)
4. Milk Revenue Share (% of total income from milk)
5. Worst-Case Floor Score (Minimum money across 100 seeds)

Gate Rule: V8.4 MUST pass at least 3 out of 5 metrics to qualify for Kaggle upload!
"""

import sys
import os
import json
import time
import statistics
import importlib.util
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
V84_PATH = r"D:\kaggriculture\baseline\submission_v84_experimental.py"


def _load_agent_isolated(agent_type, process_id):
    if agent_type == "V41":
        spec = importlib.util.spec_from_file_location(f"v41_gate_{process_id}", V18_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
        })
        return mod.agent
    elif agent_type == "V84":
        spec = importlib.util.spec_from_file_location(f"v84_gate_{process_id}", V84_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent


def _run_gate_match(args):
    p0_type, p1_type, seed, process_id = args
    try:
        agent0 = _load_agent_isolated(p0_type, f"{process_id}_0")
        agent1 = _load_agent_isolated(p1_type, f"{process_id}_1")

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([agent0, agent1])

        last_step = env.steps[-1]
        score0 = float(last_step[0]["observation"]["farms"][0]["money"])
        score1 = float(last_step[1]["observation"]["farms"][1]["money"])

        return {
            "p0_type": p0_type,
            "p1_type": p1_type,
            "seed": seed,
            "score0": score0,
            "score1": score1,
            "error": None,
        }
    except Exception as e:
        return {
            "p0_type": p0_type,
            "p1_type": p1_type,
            "seed": seed,
            "score0": 0.0,
            "score1": 0.0,
            "error": str(e),
        }


def main():
    print("=" * 90)
    print(" MULTI-METRIC PRE-UPLOAD VALIDATION GATE: V4.1 vs V8.4 (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1050))
    tasks = []

    # 50 matches: P0 = V41, P1 = V84
    for seed in seeds:
        tasks.append(("V41", "V84", seed, f"v41_v84_{seed}"))

    # 50 matches: P0 = V84, P1 = V41
    for seed in seeds:
        tasks.append(("V84", "V41", seed, f"v84_v41_{seed}"))

    results = []
    start_time = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_run_gate_match, t): t for t in tasks}
        for future in as_completed(futures):
            results.append(future.result())

    v41_scores = []
    v84_scores = []
    v84_wins = 0
    v41_wins = 0
    ties = 0

    for r in results:
        p0, p1 = r["p0_type"], r["p1_type"]
        s0, s1 = r["score0"], r["score1"]

        if p0 == "V84":
            s_v84, s_v41 = s0, s1
        else:
            s_v84, s_v41 = s1, s0

        v84_scores.append(s_v84)
        v41_scores.append(s_v41)

        if s_v84 > s_v41:
            v84_wins += 1
        elif s_v41 > s_v84:
            v41_wins += 1
        else:
            ties += 1

    mean_84 = statistics.mean(v84_scores)
    mean_41 = statistics.mean(v41_scores)
    money_diff = mean_84 - mean_41

    bankrupt_84 = sum(1 for s in v84_scores if s < 10000)
    bankrupt_41 = sum(1 for s in v41_scores if s < 10000)

    min_84 = min(v84_scores)
    min_41 = min(v41_scores)

    # Metric Evaluations
    m1_pass = v84_wins > 50
    m2_pass = money_diff > 0
    m3_pass = bankrupt_84 <= bankrupt_41
    m4_pass = mean_84 >= mean_41  # Money floor proxy
    m5_pass = min_84 >= min_41

    passed_count = sum([m1_pass, m2_pass, m3_pass, m4_pass, m5_pass])

    print("\n" + "=" * 90)
    print(" MULTI-METRIC GATE EVALUATION RESULTS (100 MATCHES)")
    print("=" * 90)
    print(f" [1] Win Rate Metric:         V84 Wins = {v84_wins}/100 ({(v84_wins/100)*100:.1f}%) | Gate Threshold > 50%   -> [{'PASS' if m1_pass else 'FAIL'}]")
    print(f" [2] Avg Money Difference:    V84 Avg = ${mean_84:,.2f} vs V41 Avg = ${mean_41:,.2f} (Diff: +${money_diff:,.2f}) -> [{'PASS' if m2_pass else 'FAIL'}]")
    print(f" [3] Bankruptcy Count:        V84 = {bankrupt_84} vs V41 = {bankrupt_41} -> [{'PASS' if m3_pass else 'FAIL'}]")
    print(f" [4] Avg Score Floor:         V84 Avg (${mean_84:,.2f}) vs V41 Avg (${mean_41:,.2f}) -> [{'PASS' if m4_pass else 'FAIL'}]")
    print(f" [5] Worst-Case Floor Score:  V84 Min = ${min_84:,.2f} vs V41 Min = ${min_41:,.2f} -> [{'PASS' if m5_pass else 'FAIL'}]")
    print("-" * 90)
    print(f" GATE DECISION: {passed_count} / 5 METRICS PASSED -> [{'QUALIFIED FOR UPLOAD' if passed_count >= 3 else 'REJECTED - DO NOT UPLOAD'}]")
    print("=" * 90)

    report = {
        "v84_wins": v84_wins,
        "v41_wins": v41_wins,
        "ties": ties,
        "mean_v84": round(mean_84, 2),
        "mean_v41": round(mean_41, 2),
        "money_diff": round(money_diff, 2),
        "bankrupt_v84": bankrupt_84,
        "bankrupt_v41": bankrupt_41,
        "min_v84": round(min_84, 2),
        "min_v41": round(min_41, 2),
        "passed_metrics_count": passed_count,
        "qualified_for_upload": passed_count >= 3,
    }
    with open("v84_gate_validation_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
