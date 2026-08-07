"""Phased Benchmark Runner for V8.2 Experimental Agent.

Runs 100-match benchmarks for submission_v82_exp.py (Seeds 1000-1099)
and verifies score parity / improvement over V8.1 ($121,973.63 baseline).
"""

import sys
import os
import json
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages")
sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments
from submission_v82_exp import agent as v82_agent


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_single_match(seed):
    try:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([v82_agent, _noop_agent])

        last_step = env.steps[-1]
        score = last_step[0]["observation"]["farms"][0]["money"]
        turn360_step = env.steps[360] if len(env.steps) > 360 else last_step
        score_t360 = turn360_step[0]["observation"]["farms"][0]["money"]

        return {"seed": seed, "score": score, "score_t360": score_t360, "error": None}
    except Exception as e:
        return {"seed": seed, "score": 0, "score_t360": 0, "error": str(e)}


def run_phase_benchmark(phase_name: str, num_matches: int = 100, max_workers: int = 8):
    print("=" * 70)
    print(f" OFFICIAL 100-MATCH BENCHMARK: V8.2 Experimental — {phase_name}")
    print(f" Target Baseline to Beat: $121,973.63 (V8.1 Baseline)")
    print("=" * 70)

    start_time = time.time()
    seeds = list(range(1000, 1000 + num_matches))
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_seed = {executor.submit(_run_single_match, seed): seed for seed in seeds}
        completed = 0
        for future in as_completed(future_to_seed):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 10 == 0 or completed == num_matches:
                elapsed = time.time() - start_time
                print(f"  Progress: {completed}/{num_matches} matches ({elapsed:.1f}s)")

    results.sort(key=lambda r: r["seed"])
    scores = [r["score"] for r in results if r["error"] is None]
    scores_t360 = [r["score_t360"] for r in results if r["error"] is None]
    elapsed = time.time() - start_time

    avg_score = statistics.mean(scores) if scores else 0
    med_score = statistics.median(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
    avg_t360 = statistics.mean(scores_t360) if scores_t360 else 0

    print("\n" + "=" * 70)
    print(f" BENCHMARK REPORT: V8.2 {phase_name}")
    print("=" * 70)
    print(f" Matches Evaluated:\t{num_matches}")
    print(f" Average Score:\t\t${avg_score:12,.2f}  (V8.1 Baseline: $121,973.63)")
    print(f" Median Score:\t\t${med_score:12,.2f}")
    print(f" Standard Dev:\t\t${stdev_score:12,.2f}")
    print(f" Best (Peak) Score:\t${max_score:12,.2f}")
    print(f" Worst Score:\t\t${min_score:12,.2f}")
    print(f" Day 15 (T360) Avg:\t${avg_t360:12,.2f}")
    print(f" Wall-Clock Time:\t{elapsed:.1f} seconds")
    print("=" * 70)

    delta = avg_score - 121973.63
    if delta >= 0:
        print(f"\n[PHASE PASSED] Score change: +${delta:,.2f}. Performance maintained/improved!")
    else:
        print(f"\n[PHASE REJECTED] Score change: -${abs(delta):,.2f}. Score dropped below $121.97k baseline.")

    return avg_score


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "Phase 1: Telemetry Collection Only"
    run_phase_benchmark(phase_name=phase, num_matches=100)
