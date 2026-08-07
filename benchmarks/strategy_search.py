"""Parallelized Parameterized Strategy Search Harness for Kaggle Agriculture.

Uses V18's configure_strategy(overrides) to test arbitrary
(strawberries, cows, sheep, melons, expansion_day) combinations
in official kaggle-environments, parallelized across CPU cores.

Usage:
    from strategy_search import run_strategy, run_strategy_batch
"""

import sys
import os
import json
import time
import importlib.util
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages")
sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

_MOD_COUNTER = 0


def _load_v18_module(mod_id=0):
    """Load a FRESH copy of the V18 module to avoid state leakage between configs."""
    v18_path = r"D:\kaggleculture_repo\kaggleculture-main\reference\kaitofukami-v18.py"
    spec = importlib.util.spec_from_file_location(f"v18_inst_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    """Do-nothing opponent."""
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_single_match_worker(args):
    """Worker function for running a single match in a separate process."""
    strategy_overrides, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(strategy_overrides)
        overrides["use_fixed_schedule"] = False  # Always autonomous
        mod.configure_strategy(overrides)

        env = kaggle_environments.make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": seed}
        )
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = last_step[0]["observation"]["farms"][0]["money"]
        return {"seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"seed": seed, "score": 0, "error": str(e)}


def run_strategy(strategy_overrides: dict, seeds: list, label: str = "", max_workers: int = 8) -> dict:
    """Run a single strategy across multiple seeds in parallel and return metrics."""
    scores = []
    per_seed = []

    tasks = [(strategy_overrides, seed, idx) for idx, seed in enumerate(seeds)]

    if len(seeds) == 1:
        res = _run_single_match_worker(tasks[0])
        scores.append(res["score"])
        per_seed.append(res)
    else:
        with ProcessPoolExecutor(max_workers=min(max_workers, len(seeds))) as executor:
            futures = [executor.submit(_run_single_match_worker, task) for task in tasks]
            for future in as_completed(futures):
                res = future.result()
                scores.append(res["score"])
                per_seed.append(res)

    avg = statistics.mean(scores) if scores else 0
    med = statistics.median(scores) if scores else 0
    std = statistics.stdev(scores) if len(scores) > 1 else 0

    return {
        "label": label,
        "overrides": strategy_overrides,
        "scores": scores,
        "avg": round(avg, 1),
        "median": round(med, 1),
        "best": max(scores) if scores else 0,
        "worst": min(scores) if scores else 0,
        "std": round(std, 1),
        "per_seed": per_seed,
    }


def _run_strategy_tuple_worker(args):
    label, overrides, seeds, worker_id = args
    res = run_strategy(overrides, seeds, label, max_workers=1)
    return res


def run_strategy_batch(strategies: list, seeds: list, output_file: str = None, max_workers: int = 8) -> list:
    """Run multiple strategies across seeds in parallel."""
    results = []
    total = len(strategies)
    start = time.time()

    print(f"Executing batch of {total} strategies across {len(seeds)} seeds using {max_workers} worker processes...")

    # Flatten all (strategy, seed) pairs for maximum CPU saturation
    all_tasks = []
    for idx, (label, overrides) in enumerate(strategies):
        for seed_idx, seed in enumerate(seeds):
            all_tasks.append((idx, label, overrides, seed, len(all_tasks)))

    # Process all matches in parallel
    match_results = {}
    done_count = 0
    total_matches = len(all_tasks)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(_run_single_match_worker, (task[2], task[3], task[4])): task
            for task in all_tasks
        }

        for future in as_completed(future_to_task):
            strat_idx, label, overrides, seed, _ = future_to_task[future]
            res = future.result()
            if strat_idx not in match_results:
                match_results[strat_idx] = {"label": label, "overrides": overrides, "scores": [], "per_seed": []}
            match_results[strat_idx]["scores"].append(res["score"])
            match_results[strat_idx]["per_seed"].append(res)
            done_count += 1
            if done_count % 10 == 0 or done_count == total_matches:
                elapsed = time.time() - start
                eta = (elapsed / done_count) * (total_matches - done_count)
                print(f"  Progress: {done_count}/{total_matches} matches done ({elapsed:.1f}s, ETA {eta:.0f}s)")

    # Aggregate results per strategy
    for idx in range(total):
        data = match_results[idx]
        scores = data["scores"]
        avg = statistics.mean(scores) if scores else 0
        med = statistics.median(scores) if scores else 0
        std = statistics.stdev(scores) if len(scores) > 1 else 0

        results.append({
            "label": data["label"],
            "overrides": data["overrides"],
            "scores": scores,
            "avg": round(avg, 1),
            "median": round(med, 1),
            "best": max(scores) if scores else 0,
            "worst": min(scores) if scores else 0,
            "std": round(std, 1),
            "per_seed": data["per_seed"],
        })

    # Sort by average score descending
    results.sort(key=lambda r: r["avg"], reverse=True)

    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")

    return results


def print_leaderboard(results: list, top_n: int = 20):
    """Print a ranked leaderboard of strategies."""
    print(f"\n{'='*90}")
    print(f"{'Rank':>4} | {'Label':<40} | {'Avg':>10} | {'Best':>10} | {'Worst':>10} | {'Std':>8}")
    print(f"{'-'*90}")
    for i, r in enumerate(results[:top_n]):
        print(f"{i+1:>4} | {r['label']:<40} | ${r['avg']:>9,.0f} | ${r['best']:>9,.0f} | ${r['worst']:>9,.0f} | ${r['std']:>7,.0f}")
    print(f"{'='*90}")


if __name__ == "__main__":
    print("Testing parallel harness on 2 strategies × 2 seeds...")
    test_strats = [
        ("Default V18", {}),
        ("High Strawberries", {"strawberries": 45})
    ]
    res = run_strategy_batch(test_strats, [1000, 1001], max_workers=4)
    print_leaderboard(res)
