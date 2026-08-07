"""Benchmark Verification Script for V8.1 and V8.2.

Completely isolates submission_v81.py and submission_v82.py evaluations across Seeds 1000-1099.
Outputs:
1. Git commit hash
2. SHA256 checksum of both submission files
3. Exact benchmark script used & seed range
4. List of bankrupt seeds (<$10,000 final score)
5. Mean, median, stddev, min, max score for both submissions
"""

import sys
import os
import json
import time
import hashlib
import subprocess
import importlib.util
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments


def get_git_hash():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=r"D:\kaggriculture")
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_HASH"


def get_file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_submission_worker(args):
    submission_path, seed, mod_id = args
    try:
        spec = importlib.util.spec_from_file_location(f"sub_mod_{mod_id}", submission_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"seed": seed, "score": 0.0, "error": str(e)}


def evaluate_submission_clean(submission_path, seeds=list(range(1000, 1100))):
    tasks = [(submission_path, seed, idx) for idx, seed in enumerate(seeds)]
    scores_by_seed = {}

    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_run_submission_worker, task): task for task in tasks}
        for future in as_completed(futures):
            res = future.result()
            scores_by_seed[res["seed"]] = res["score"]

    ordered_scores = [scores_by_seed[s] for s in seeds]
    bankrupt_seeds = [s for s, sc in scores_by_seed.items() if sc < 10000.0]

    return {
        "mean": statistics.mean(ordered_scores),
        "median": statistics.median(ordered_scores),
        "std_dev": statistics.stdev(ordered_scores),
        "min": min(ordered_scores),
        "max": max(ordered_scores),
        "bankrupt_seeds": bankrupt_seeds,
        "bankrupt_count": len(bankrupt_seeds),
        "scores": ordered_scores,
    }


def main():
    print("=" * 85)
    print(" BENCHMARK VERIFICATION REPORT")
    print("=" * 85)

    git_hash = get_git_hash()
    print(f" Git Commit Hash:      {git_hash}")
    print(f" Benchmark Seeds:      Seeds 1000 to 1099 (100 Matches)")
    print(f" Evaluation Engine:    Kaggle Agriculture Environment (720 steps)")
    print("-" * 85)

    v81_path = r"D:\kaggriculture\baseline\submission_v81.py"
    v82_path = r"D:\kaggriculture\baseline\submission_v82.py"

    v81_sha = get_file_sha256(v81_path)
    v82_sha = get_file_sha256(v82_path)

    print(f" V8.1 File Path:       {v81_path}")
    print(f" V8.1 SHA256:          {v81_sha}")
    print(f" V8.2 File Path:       {v82_path}")
    print(f" V8.2 SHA256:          {v82_sha}")
    print("-" * 85)

    print("Running clean 100-match evaluation for submission_v81.py...")
    t0 = time.time()
    v81_res = evaluate_submission_clean(v81_path)
    print(f"V8.1 evaluation completed in {time.time()-t0:.1f}s.")

    print("\nRunning clean 100-match evaluation for submission_v82.py...")
    t0 = time.time()
    v82_res = evaluate_submission_clean(v82_path)
    print(f"V8.2 evaluation completed in {time.time()-t0:.1f}s.")

    print("\n" + "=" * 95)
    print(" VERIFIED 100-MATCH COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Submission File':<22} | {'Mean ($)':<12} | {'Median ($)':<12} | {'StdDev ($)':<10} | {'Min ($)':<10} | {'Max ($)':<10} | {'Bankruptcies':<12}")
    print("-" * 105)
    print(f"{'submission_v81.py':<22} | ${v81_res['mean']:<11,.2f} | ${v81_res['median']:<11,.2f} | ${v81_res['std_dev']:<9,.2f} | ${v81_res['min']:<9,.2f} | ${v81_res['max']:<9,.2f} | {v81_res['bankrupt_count']:<12}")
    print(f"{'submission_v82.py':<22} | ${v82_res['mean']:<11,.2f} | ${v82_res['median']:<11,.2f} | ${v82_res['std_dev']:<9,.2f} | ${v82_res['min']:<9,.2f} | ${v82_res['max']:<9,.2f} | {v82_res['bankrupt_count']:<12}")
    print("=" * 95)

    print("\nBANKRUPT SEED ANALYSIS:")
    print(f" V8.1 Bankrupt Seeds (<$10k): {v81_res['bankrupt_seeds']}")
    print(f" V8.2 Bankrupt Seeds (<$10k): {v82_res['bankrupt_seeds']}")

    diff = v82_res["mean"] - v81_res["mean"]
    print(f"\nVERIFIED GAIN (V8.2 vs V8.1): +${diff:,.2f} across 100 matches!")

    report = {
        "git_commit_hash": git_hash,
        "seed_range": "1000-1099",
        "submission_v81": {
            "file": "baseline/submission_v81.py",
            "sha256": v81_sha,
            "results": v81_res,
        },
        "submission_v82": {
            "file": "baseline/submission_v82.py",
            "sha256": v82_sha,
            "results": v82_res,
        },
        "net_gain": round(diff, 2),
    }

    with open("benchmark_verification_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved benchmark_verification_results.json")


if __name__ == "__main__":
    main()
