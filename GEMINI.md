# Antigravity Rules: Kaggriculture

## Parallel Evaluation Directive (MANDATORY)
* **Parallel Execution with 10 Workers**: Hereafter, every evaluation run, mechanism suite, candidate sweep, and batch simulation MUST execute in parallel across **10 worker processes** (`max_workers=10`).
* Never run batch simulation episodes serially in a single-threaded loop.
* Always use `concurrent.futures.ProcessPoolExecutor(max_workers=10)` or `multiprocessing.Pool(processes=10)` to parallelize match evaluations.
* Ensure all multiprocessing scripts use standard `__main__` entrypoints (`if __name__ == '__main__':`) for full Windows multiprocessing compatibility.

## Mandatory V4.1 Benchmark Opponent Directive (MANDATORY)
* **Never Deploy on Local-Only Metrics**: Never deploy or promote any candidate to the live leaderboard based solely on local self-play or static replay action gauntlets.
* **Mandatory V4.1 Head-to-Head Gate**: Every candidate must be benchmarked head-to-head against proven live champion V4.1 (`baseline/kaitofukami-v18.py`) in dynamic, 2-player live simulations across both seats (Seat 0 and Seat 1) across diverse seeds using 10 parallel workers (`max_workers=10`).
* **Dual Statistical Significance Standard**: A candidate is NOT proven by win rate alone. To pass the gate, it must achieve **BOTH**:
  1. Win rate >= 55.0% in dynamic seat-swapped head-to-head matches against V4.1.
  2. Strictly positive mean wealth delta against V4.1 with the lower bound of the 95% bootstrap confidence interval strictly greater than $0 (Delta_mean > $0 and CI_95_low > $0).
* **Live Deployment Freeze**: `submission.py` is strictly reserved for the proven live production baseline (V4.1). All experimental bots (RC18, Q1–Q3, RC20+) must remain quarantined in `candidates/` or `scratch/` files until this gate is mathematically cleared.


