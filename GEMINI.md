# Antigravity Rules: Kaggriculture

## Parallel Evaluation Directive (MANDATORY)
* **Parallel Execution with 10 Workers**: Hereafter, every evaluation run, mechanism suite, candidate sweep, and batch simulation MUST execute in parallel across **10 worker processes** (`max_workers=10`).
* Never run batch simulation episodes serially in a single-threaded loop.
* Always use `concurrent.futures.ProcessPoolExecutor(max_workers=10)` or `multiprocessing.Pool(processes=10)` to parallelize match evaluations.
* Ensure all multiprocessing scripts use standard `__main__` entrypoints (`if __name__ == '__main__':`) for full Windows multiprocessing compatibility.

## Mandatory V4.1 Benchmark Opponent Directive (MANDATORY)
* **Never Deploy on Local-Only Metrics**: Never deploy or promote any candidate to the live leaderboard based solely on local self-play or static replay action gauntlets.
* **Mandatory V4.1 Head-to-Head Gate**: Every candidate must be benchmarked head-to-head against proven live champion V4.1 (`baseline/kaitofukami-v18.py`) in dynamic, 2-player live simulations across both seats (Seat 0 and Seat 1) across diverse seeds using 10 parallel workers (`max_workers=10`).
* **Live Deployment Freeze**: `submission.py` is reserved for proven live ratings. All experimental bots (RC18, Q1-Q3, RC20+) must remain isolated in candidate/scratch files until they beat V4.1 head-to-head.

