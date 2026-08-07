"""Official Parallel 100-Match Benchmark for V8.1 Autonomous Agent (submission.py).

Executes 100 matches (Seeds 1000 to 1099) in official kaggle-environments (720 steps)
parallelized across CPU cores, measuring:
- Average Score
- Median Score
- Standard Deviation
- Best (Peak) Score
- Worst Score
- Day 15 (Turn 360) Score
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
from submission import agent as v81_agent


def _noop_agent(obs):
    """Do-nothing opponent."""
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_single_match(seed):
    """Runs a single 720-step match for a given seed."""
    try:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([v81_agent, _noop_agent])

        last_step = env.steps[-1]
        score = last_step[0]["observation"]["farms"][0]["money"]

        turn360_step = env.steps[360] if len(env.steps) > 360 else last_step
        score_t360 = turn360_step[0]["observation"]["farms"][0]["money"]

        return {"seed": seed, "score": score, "score_t360": score_t360, "error": None}
    except Exception as e:
        return {"seed": seed, "score": 0, "score_t360": 0, "error": str(e)}


def run_100_matches_benchmark(num_matches: int = 100, max_workers: int = 8):
    print("==================================================")
    print(f" OFFICIAL KAGGLE-ENVIRONMENTS 100-MATCH BENCHMARK")
    print(f" V8.1 Strategy_15 Agent (Seeds 1000 to {1000 + num_matches - 1})")
    print("==================================================")

    start_time = time.time()
    seeds = list(range(1000, 1000 + num_matches))
    results = []

    print(f"Executing {num_matches} matches in parallel using {max_workers} worker processes...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_seed = {executor.submit(_run_single_match, seed): seed for seed in seeds}
        completed = 0
        for future in as_completed(future_to_seed):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 10 == 0 or completed == num_matches:
                elapsed = time.time() - start_time
                eta = (elapsed / completed) * (num_matches - completed)
                print(f"  Progress: {completed}/{num_matches} matches done ({elapsed:.1f}s, ETA {eta:.0f}s)")

    # Sort by seed
    results.sort(key=lambda r: r["seed"])
    scores = [r["score"] for r in results if r["error"] is None]
    scores_t360 = [r["score_t360"] for r in results if r["error"] is None]

    elapsed = time.time() - start_time

    # Calculate statistics
    avg_score = statistics.mean(scores) if scores else 0
    med_score = statistics.median(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
    avg_t360 = statistics.mean(scores_t360) if scores_t360 else 0

    report = {
        "num_matches": num_matches,
        "elapsed_seconds": round(elapsed, 2),
        "v81_agent": {
            "average": round(avg_score, 2),
            "median": round(med_score, 2),
            "best_peak": round(max_score, 2),
            "worst": round(min_score, 2),
            "stdev": round(stdev_score, 2),
            "day15_t360_average": round(avg_t360, 2),
        },
        "per_seed": results
    }

    # Save to metrics.json
    metrics_path = os.path.join(os.path.dirname(__file__), "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 65)
    print(f" OFFICIAL 100-MATCH BENCHMARK REPORT (V8.1 Strategy_15 Agent)")
    print("=" * 65)
    print(f" Matches Evaluated:\t{num_matches}")
    print(f" Average Score:\t\t${avg_score:12,.2f}")
    print(f" Median Score:\t\t${med_score:12,.2f}")
    print(f" Standard Dev:\t\t${stdev_score:12,.2f}")
    print(f" Best (Peak) Score:\t${max_score:12,.2f}")
    print(f" Worst Score:\t\t${min_score:12,.2f}")
    print(f" Day 15 (T360) Avg:\t${avg_t360:12,.2f}")
    print(f" Total Wall Time:\t{elapsed:.1f} seconds")
    print("=" * 65)

    if avg_score >= 118000.0:
        print(f"\n[STABLE BASELINE CONFIRMED] V8.1 Agent average score is ${avg_score:,.2f} (>= $118k threshold)!")
    else:
        print(f"\n[NOTICE] 100-match average is ${avg_score:,.2f}.")

    return report


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_100_matches_benchmark(num_matches=count)
