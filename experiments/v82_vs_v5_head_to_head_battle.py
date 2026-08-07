"""Head-to-Head Battle: V8.2 Baseline (submission_v82_cows13.py) vs V5 Agent (D:\\kaggleculture\\V5_RESEARCH_START).

Executes 200 direct 1v1 competitive matches across 100 official benchmark seeds (Seeds 1000-1099).
- Round 1 (100 matches): Player 0 = V8.2 Baseline, Player 1 = V5 Agent
- Round 2 (100 matches): Player 0 = V5 Agent, Player 1 = V8.2 Baseline (swapped seats)

Logs:
- Win / Loss / Tie Counts
- Average Final Money ($) for both agents
- Head-to-Head Victory Margin ($)
- Bankruptcies count
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

# Ensure D:\kaggleculture\V5_RESEARCH_START is in Python sys.path
V5_ROOT = r"D:\kaggleculture\V5_RESEARCH_START"
if V5_ROOT not in sys.path:
    sys.path.insert(0, V5_ROOT)

V82_BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 13,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _load_v18_module(process_id):
    v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
    if not os.path.exists(v18_path):
        v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    spec = importlib.util.spec_from_file_location(f"v18_h2h_{process_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))
    return mod.agent


def _load_v5_agent(process_id):
    if V5_ROOT not in sys.path:
        sys.path.insert(0, V5_ROOT)
    import future_submission.entrypoint as v5_entry
    return v5_entry.agent_fn


def run_h2h_match(args):
    p0_type, p1_type, seed, process_id = args
    try:
        if p0_type == "V82":
            agent0 = _load_v18_module(process_id)
            agent1 = _load_v5_agent(process_id)
        else:
            agent0 = _load_v5_agent(process_id)
            agent1 = _load_v18_module(process_id)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([agent0, agent1])

        last_step = env.steps[-1]
        score0 = float(last_step[0]["observation"]["farms"][0]["money"])
        score1 = float(last_step[1]["observation"]["farms"][1]["money"])

        if p0_type == "V82":
            v82_score, v5_score = score0, score1
        else:
            v82_score, v5_score = score1, score0

        return {
            "seed": seed,
            "p0_type": p0_type,
            "v82_score": v82_score,
            "v5_score": v5_score,
            "winner": "V82" if v82_score > v5_score else ("V5" if v5_score > v82_score else "TIE"),
            "margin": v82_score - v5_score,
            "error": None,
        }
    except Exception as e:
        return {
            "seed": seed,
            "p0_type": p0_type,
            "v82_score": 0.0,
            "v5_score": 0.0,
            "winner": "ERROR",
            "margin": 0.0,
            "error": str(e),
        }


def main():
    print("=" * 90)
    print(" HEAD-TO-HEAD BATTLE: V8.2 BASELINE vs V5 RESEARCH AGENT (200 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    # Match Round 1: V8.2 (P0) vs V5 (P1)
    print("\n--- ROUND 1: V8.2 Baseline (Player 0) vs V5 Agent (Player 1) [100 Seeds] ---")
    r1_tasks = [("V82", "V5", seed, seed) for seed in seeds]
    r1_results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_h2h_match, task): task for task in r1_tasks}
        for future in as_completed(futures):
            res = future.result()
            r1_results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                v82_avg = statistics.mean([r["v82_score"] for r in r1_results])
                v5_avg = statistics.mean([r["v5_score"] for r in r1_results])
                print(f"  [Round 1 Progress {completed}/100] V8.2 Avg: ${v82_avg:,.2f} | V5 Avg: ${v5_avg:,.2f}")

    # Match Round 2: V5 (P0) vs V8.2 (P1) - Seat Swap
    print("\n--- ROUND 2: V5 Agent (Player 0) vs V8.2 Baseline (Player 1) [100 Seeds] ---")
    r2_tasks = [("V5", "V82", seed, seed + 5000) for seed in seeds]
    r2_results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_h2h_match, task): task for task in r2_tasks}
        for future in as_completed(futures):
            res = future.result()
            r2_results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                v82_avg = statistics.mean([r["v82_score"] for r in r2_results])
                v5_avg = statistics.mean([r["v5_score"] for r in r2_results])
                print(f"  [Round 2 Progress {completed}/100] V8.2 Avg: ${v82_avg:,.2f} | V5 Avg: ${v5_avg:,.2f}")

    elapsed = time.time() - start_time
    all_results = r1_results + r2_results

    # Aggregate global match statistics
    v82_wins = sum(1 for r in all_results if r["winner"] == "V82")
    v5_wins = sum(1 for r in all_results if r["winner"] == "V5")
    ties = sum(1 for r in all_results if r["winner"] == "TIE")

    v82_all_scores = [r["v82_score"] for r in all_results]
    v5_all_scores = [r["v5_score"] for r in all_results]

    v82_mean = statistics.mean(v82_all_scores)
    v82_median = statistics.median(v82_all_scores)
    v82_std = statistics.stdev(v82_all_scores)
    v82_worst = min(v82_all_scores)

    v5_mean = statistics.mean(v5_all_scores)
    v5_median = statistics.median(v5_all_scores)
    v5_std = statistics.stdev(v5_all_scores)
    v5_worst = min(v5_all_scores)

    avg_margin = statistics.mean([r["margin"] for r in all_results])

    print("\n" + "=" * 95)
    print(" HEAD-TO-HEAD BATTLE FINAL SUMMARY (200 MATCHES EVALUATED)")
    print("=" * 95)
    print(f" V8.2 Baseline Wins:            {v82_wins} / 200 matches ({(v82_wins/200)*100:.1f}%)")
    print(f" V5 Research Agent Wins:        {v5_wins} / 200 matches ({(v5_wins/200)*100:.1f}%)")
    print(f" Ties / Equal Scores:           {ties} / 200 matches")
    print("-" * 95)
    print(f" V8.2 Baseline Avg Score:       ${v82_mean:,.2f} (Median: ${v82_median:,.2f}, Worst: ${v82_worst:,.2f}, StdDev: ${v82_std:,.2f})")
    print(f" V5 Research Agent Avg Score:   ${v5_mean:,.2f} (Median: ${v5_median:,.2f}, Worst: ${v5_worst:,.2f}, StdDev: ${v5_std:,.2f})")
    print(f" Head-to-Head Victory Margin:   +${avg_margin:,.2f} per match in favor of {'V8.2 Baseline' if avg_margin > 0 else 'V5 Agent'}")
    print("=" * 95)

    if v82_wins > v5_wins:
        verdict = f"V8.2 BASELINE DOMINATES! V8.2 won {v82_wins}/200 matches ({(v82_wins/200)*100:.1f}% win rate) with average margin of +${avg_margin:,.2f} per game."
    elif v5_wins > v82_wins:
        verdict = f"V5 AGENT WINS! V5 won {v5_wins}/200 matches with average margin of +${-avg_margin:,.2f} per game."
        
    else:
        verdict = "MATCH TIED! Both agents performed equally across 200 matches."

    print(f"\nFINAL BATTLE VERDICT: {verdict}\n")

    report = {
        "v82_wins": v82_wins,
        "v5_wins": v5_wins,
        "ties": ties,
        "v82_win_rate_pct": round((v82_wins / 200) * 100, 2),
        "v82_stats": {
            "mean": round(v82_mean, 2),
            "median": round(v82_median, 2),
            "std_dev": round(v82_std, 2),
            "worst": round(v82_worst, 2),
        },
        "v5_stats": {
            "mean": round(v5_mean, 2),
            "median": round(v5_median, 2),
            "std_dev": round(v5_std, 2),
            "worst": round(v5_worst, 2),
        },
        "avg_victory_margin": round(avg_margin, 2),
        "final_battle_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("v82_vs_v5_head_to_head_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full battle report to v82_vs_v5_head_to_head_results.json")


if __name__ == "__main__":
    main()
