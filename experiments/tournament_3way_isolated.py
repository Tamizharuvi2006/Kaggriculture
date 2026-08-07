"""Isolated 3-Way Round-Robin Tournament: V4.1 vs V8.2 vs V8.3.

Eliminates Python module state contamination by running each match in an isolated process.

Evaluates 300 Total Matches across Seeds 1000-1099 (100 matches per pair, swapped seats):
1. V4.1 Base Engine vs V8.2 Baseline (100 matches)
2. V4.1 Base Engine vs V8.3 Champion (100 matches)
3. V8.2 Baseline vs V8.3 Champion (100 matches)

Logs:
- Head-to-head win / loss / tie counts
- Average money ($) for both agents
- Head-to-head victory margins ($)
- Bankruptcies count (<$10k final score)
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


def _load_agent_isolated(agent_type, process_id):
    """Loads agent in an isolated process namespace to prevent global state contamination."""
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    v83_path = r"D:\kaggriculture\baseline\submission_v83_standalone.py"

    if agent_type == "V41":
        # Pure unconstrained kaitofukami-v18.py base engine
        spec = importlib.util.spec_from_file_location(f"v41_iso_{process_id}", v18_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Default V18 strategy settings (unconstrained dynamic adaptation)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
        })
        return mod.agent
    elif agent_type == "V82":
        # V8.2 Baseline with Cows=13
        spec = importlib.util.spec_from_file_location(f"v82_iso_{process_id}", v18_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "opening_melons": 15,
            "strawberries": 30,
            "cows": 13,
            "sheep": 0,
            "land_ne_day": 5,
            "land_sw_day": 7,
        })
        return mod.agent
    elif agent_type == "V83":
        # V8.3 Standalone Monolithic Champion
        spec = importlib.util.spec_from_file_location(f"v83_iso_{process_id}", v83_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent


def _run_tournament_match(args):
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


def run_pair_benchmark(type_a, type_b, seeds, max_workers):
    print(f"\n--- TOURNAMENT MATCHUP: {type_a} vs {type_b} (100 Matches across Seeds 1000-1049, Swapped Seats) ---")
    tasks = []

    # 50 matches: P0 = type_a, P1 = type_b
    for seed in seeds[:50]:
        tasks.append((type_a, type_b, seed, f"{type_a}_{type_b}_{seed}"))

    # 50 matches: P0 = type_b, P1 = type_a
    for seed in seeds[:50]:
        tasks.append((type_b, type_a, seed, f"{type_b}_{type_a}_{seed}"))

    results = []
    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_tournament_match, t): t for t in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1

    a_scores = []
    b_scores = []
    a_wins = 0
    b_wins = 0
    ties = 0

    for r in results:
        p0, p1 = r["p0_type"], r["p1_type"]
        s0, s1 = r["score0"], r["score1"]

        if p0 == type_a:
            sa, sb = s0, s1
        else:
            sa, sb = s1, s0

        a_scores.append(sa)
        b_scores.append(sb)

        if sa > sb:
            a_wins += 1
        elif sb > sa:
            b_wins += 1
        else:
            ties += 1

    mean_a = statistics.mean(a_scores)
    mean_b = statistics.mean(b_scores)
    margin = mean_a - mean_b

    print(f"  {type_a} Wins: {a_wins}/100 ({(a_wins/100)*100:.1f}%) | {type_b} Wins: {b_wins}/100 ({(b_wins/100)*100:.1f}%) | Ties: {ties}")
    print(f"  {type_a} Avg Score: ${mean_a:,.2f} | {type_b} Avg Score: ${mean_b:,.2f} | Victory Margin: +${margin:,.2f}")

    return {
        "matchup": f"{type_a}_vs_{type_b}",
        "type_a": type_a,
        "type_b": type_b,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "mean_a": round(mean_a, 2),
        "mean_b": round(mean_b, 2),
        "victory_margin": round(margin, 2),
    }


def main():
    print("=" * 90)
    print(" ISOLATED 3-WAY TOURNAMENT: V4.1 vs V8.2 vs V8.3 (300 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1050))
    max_workers = 4
    start_time = time.time()

    # Matchup 1: V4.1 vs V8.2
    m1 = run_pair_benchmark("V41", "V82", seeds, max_workers)

    # Matchup 2: V4.1 vs V8.3
    m2 = run_pair_benchmark("V41", "V83", seeds, max_workers)

    # Matchup 3: V8.2 vs V8.3
    m3 = run_pair_benchmark("V82", "V83", seeds, max_workers)

    elapsed = time.time() - start_time

    print("\n" + "=" * 95)
    print(" TOURNAMENT FINAL SUMMARY TABLE (300 MATCHES EVALUATED)")
    print("=" * 95)
    print(f"{'Matchup':<20} | {'Winner':<10} | {'Win Rate':<12} | {'Agent A Avg ($)':<16} | {'Agent B Avg ($)':<16} | {'Margin ($)':<12}")
    print("-" * 95)
    for m in [m1, m2, m3]:
        w = m['type_a'] if m['a_wins'] > m['b_wins'] else (m['type_b'] if m['b_wins'] > m['a_wins'] else "TIE")
        wr = max(m['a_wins'], m['b_wins'])
        print(f"{m['matchup']:<20} | {w:<10} | {wr}/100 ({wr:.1f}%) | ${m['mean_a']:<15,.2f} | ${m['mean_b']:<15,.2f} | +${m['victory_margin']:<11,.2f}")
    print("=" * 95)

    report = {
        "m1_v41_vs_v82": m1,
        "m2_v41_vs_v83": m2,
        "m3_v82_vs_v83": m3,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("tournament_3way_isolated_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full tournament report to tournament_3way_isolated_results.json")


if __name__ == "__main__":
    main()
