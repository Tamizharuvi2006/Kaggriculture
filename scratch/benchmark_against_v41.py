"""Mandatory V4.1 Benchmark Harness (10 Workers, ProcessPoolExecutor).

Every candidate must pass this benchmark before any consideration for live deployment.
Evaluates the candidate against proven live champion V4.1 (`baseline/kaitofukami-v18.py`)
in dynamic, 2-player head-to-head matches across both Seat 0 and Seat 1.
"""

import sys
import os
import time
import argparse
import numpy as np
import concurrent.futures
import kaggle_environments

sys.path.insert(0, r"D:\kaggriculture")

TOURNAMENT_SEEDS = [
    953494806, 711226357, 1624303674, 1362511072, 529528835,
    198057751, 2088147978, 805234002, 1262472034, 1802332305,
    1396349514, 2038933214, 1098481434, 1294246960, 114674719,
    1097619213, 1024364491, 1026490656, 1729007684, 1845173322
]

V41_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

def _run_single_h2h(args):
    cand_path, seat, seed, match_label = args
    import types
    
    # Load candidate
    cand_mod = types.ModuleType("candidate_mod")
    with open(cand_path, "r", encoding="utf-8") as f:
        exec(f.read(), cand_mod.__dict__)
        
    # Load V4.1
    v41_mod = types.ModuleType("v41_mod")
    with open(V41_PATH, "r", encoding="utf-8") as f:
        exec(f.read(), v41_mod.__dict__)
        
    p0 = cand_mod.agent if seat == 0 else v41_mod.agent
    p1 = v41_mod.agent if seat == 0 else cand_mod.agent
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    for _ in range(720):
        if env.done:
            break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        try:
            act0 = p0(obs0)
        except Exception:
            act0 = {}
        try:
            act1 = p1(obs1)
        except Exception:
            act1 = {}
        env.step([act0, act1])
        
    s0 = int(env.state[0].observation["farms"][0]["money"])
    s1 = int(env.state[1].observation["farms"][1]["money"])
    
    cand_score = s0 if seat == 0 else s1
    v41_score = s1 if seat == 0 else s0
    
    return {
        "label": match_label,
        "seed": seed,
        "cand_seat": seat,
        "cand_score": cand_score,
        "v41_score": v41_score,
        "delta": cand_score - v41_score,
    }

def benchmark_against_v41(cand_path: str, num_seeds: int = 10):
    if not os.path.exists(cand_path):
        raise FileNotFoundError(f"Candidate file not found: {cand_path}")
        
    cand_name = os.path.basename(cand_path)
    print("=" * 88)
    print(f"MANDATORY V4.1 BENCHMARK GATE: {cand_name} vs V4.1 Clean (10 Workers, {num_seeds} Seeds, Seat Swap)")
    print("=" * 88)
    
    tasks = []
    seeds = TOURNAMENT_SEEDS[:num_seeds]
    for i, s in enumerate(seeds):
        tasks.append((cand_path, 0, s, f"Seed_{i+1}_Seat0"))
        tasks.append((cand_path, 1, s, f"Seed_{i+1}_Seat1"))
        
    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(_run_single_h2h, tasks))
    elapsed = time.time() - t0
    
    cand_scores = [r["cand_score"] for r in results]
    v41_scores = [r["v41_score"] for r in results]
    wins = sum(1 for r in results if r["delta"] > 0)
    ties = sum(1 for r in results if r["delta"] == 0)
    losses = sum(1 for r in results if r["delta"] < 0)
    
    print(f"{'Match':<18} | {'Seat':<6} | {'Candidate Score':>16} | {'V4.1 Score':>14} | {'Delta':>12} | {'Result':<6}")
    print("-" * 88)
    for r in results:
        res = "WIN" if r["delta"] > 0 else ("TIE" if r["delta"] == 0 else "LOSS")
        print(f"{r['label']:<18} | {r['cand_seat']:<6} | ${r['cand_score']:>15,d} | ${r['v41_score']:>13,d} | ${r['delta']:>+11,d} | {res:<6}")
        
    n = len(results)
    wr = (wins / n) * 100.0
    cand_mean = float(np.mean(cand_scores))
    v41_mean = float(np.mean(v41_scores))
    mean_delta = cand_mean - v41_mean
    
    deltas = np.array([r["delta"] for r in results])
    rng = np.random.default_rng(seed=42)
    boot_means = [np.mean(rng.choice(deltas, size=len(deltas), replace=True)) for _ in range(1000)]
    ci_low, ci_high = float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))
    
    passed = (wr >= 55.0 and mean_delta > 0 and ci_low > 0)

    print("=" * 88)
    print(f"GATE SUMMARY: {cand_name} vs V4.1 ({n} matches in {elapsed:.1f}s)")
    print(f"  Head-to-Head Record: {wins}W / {ties}T / {losses}L  (Win Rate: {wr:.1f}%)")
    print(f"  Candidate Wealth   : Mean ${cand_mean:,.0f} | Floor ${min(cand_scores):,d} | Ceiling ${max(cand_scores):,d}")
    print(f"  V4.1 Wealth        : Mean ${v41_mean:,.0f} | Floor ${min(v41_scores):,d} | Ceiling ${max(v41_scores):,d}")
    print(f"  Net Mean Delta     : ${mean_delta:+,.0f} per match [95% Bootstrap CI: ${ci_low:+,.0f} to ${ci_high:+,.0f}]")
    print(f"  DEPLOYMENT VERDICT : {'PASSED GATE (Strictly beats V4.1 with 95% confidence)' if passed else 'REJECTED (Does NOT strictly beat V4.1 baseline)'}")
    print("=" * 88)
    return wr, mean_delta, (ci_low, ci_high)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mandatory V4.1 benchmark on candidate bot.")
    parser.add_argument("candidate", nargs="?", default=r"D:\kaggriculture\submission_rc18.py", help="Path to candidate script")
    parser.add_argument("--seeds", type=int, default=10, help="Number of tournament seeds to evaluate (default 10)")
    args = parser.parse_args()
    
    benchmark_against_v41(args.candidate, num_seeds=args.seeds)
