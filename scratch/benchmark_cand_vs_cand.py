#!/usr/bin/env python3
"""Pairwise Head-to-Head Candidate Benchmark (10 Workers, Seat-Swapped).

Benchmarks Candidate A vs Candidate B in dynamic 2-player matches across diverse seeds.
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
    1097619213, 1024364491, 1026490656, 1729007684, 1845173322,
    1383158606, 249081663, 63710184, 1602467581, 600620971,
    535901256, 489341423, 309655412, 1591559892, 230106707,
    1463201078, 1600571865, 1925941032, 1181165722, 196699713,
    1278073012, 916070220, 78252793, 73989047, 211209005
]

def _run_single_match(args):
    cand_a_path, cand_b_path, a_seat, seed, label = args
    import types
    
    mod_a = types.ModuleType("mod_a")
    with open(cand_a_path, "r", encoding="utf-8") as f:
        exec(f.read(), mod_a.__dict__)
        
    mod_b = types.ModuleType("mod_b")
    with open(cand_b_path, "r", encoding="utf-8") as f:
        exec(f.read(), mod_b.__dict__)
        
    p0 = mod_a.agent if a_seat == 0 else mod_b.agent
    p1 = mod_b.agent if a_seat == 0 else mod_a.agent
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    for _ in range(720):
        if env.done:
            break
        try:
            act0 = p0(env.state[0].observation)
        except Exception:
            act0 = {}
        try:
            act1 = p1(env.state[1].observation)
        except Exception:
            act1 = {}
        env.step([act0, act1])
        
    s0 = int(env.state[0].observation["farms"][0]["money"])
    s1 = int(env.state[1].observation["farms"][1]["money"])
    
    score_a = s0 if a_seat == 0 else s1
    score_b = s1 if a_seat == 0 else s0
    
    return {
        "label": label,
        "seed": seed,
        "a_seat": a_seat,
        "score_a": score_a,
        "score_b": score_b,
        "delta": score_a - score_b,
    }

def benchmark_pairwise(cand_a_path: str, cand_b_path: str, num_seeds: int = 10, start_seed: int = 0):
    name_a = os.path.basename(cand_a_path)
    name_b = os.path.basename(cand_b_path)
    print("=" * 88)
    print(f"PAIRWISE BENCHMARK: {name_a} vs {name_b} (10 Workers, {num_seeds} Seeds [offset {start_seed}], Seat Swap)")
    print("=" * 88)
    
    tasks = []
    seeds = TOURNAMENT_SEEDS[start_seed:start_seed + num_seeds]
    for i, s in enumerate(seeds):
        tasks.append((cand_a_path, cand_b_path, 0, s, f"Seed_{start_seed + i + 1}_Seat0"))
        tasks.append((cand_a_path, cand_b_path, 1, s, f"Seed_{start_seed + i + 1}_Seat1"))
        
    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(_run_single_match, tasks))
    elapsed = time.time() - t0
    
    scores_a = [r["score_a"] for r in results]
    scores_b = [r["score_b"] for r in results]
    wins = sum(1 for r in results if r["delta"] > 0)
    ties = sum(1 for r in results if r["delta"] == 0)
    losses = sum(1 for r in results if r["delta"] < 0)
    n = len(results)
    wr = (wins + 0.5 * ties) / n * 100.0
    mean_a = float(np.mean(scores_a))
    mean_b = float(np.mean(scores_b))
    mean_delta = mean_a - mean_b
    deltas = [r["delta"] for r in results]
    
    rng = np.random.default_rng(seed=42)
    boot_means = [np.mean(rng.choice(deltas, size=len(deltas), replace=True)) for _ in range(1000)]
    ci_low, ci_high = float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))
    
    for r in results:
        res = "WIN" if r["delta"] > 0 else ("TIE" if r["delta"] == 0 else "LOSS")
        print(f"{r['label']:<18} | Seat {r['a_seat']} | {name_a}: ${r['score_a']:>11,d} vs {name_b}: ${r['score_b']:>11,d} | Delta: ${r['delta']:>+8,d} | {res}")
        
    print("=" * 88)
    print(f"HEAD-TO-HEAD SUMMARY: {name_a} vs {name_b} ({n} matches in {elapsed:.1f}s)")
    print(f"  Record            : {wins}W / {ties}T / {losses}L  (Win Rate: {wr:.1f}%)")
    print(f"  {name_a:<18}: Mean ${mean_a:,.0f} | Floor ${min(scores_a):,d} | Ceiling ${max(scores_a):,d}")
    print(f"  {name_b:<18}: Mean ${mean_b:,.0f} | Floor ${min(scores_b):,d} | Ceiling ${max(scores_b):,d}")
    print(f"  Net Mean Delta    : ${mean_delta:+,.0f} per match [95% Bootstrap CI: ${ci_low:+,.0f} to ${ci_high:+,.0f}]")
    print("=" * 88)
    return wr, mean_delta, (ci_low, ci_high)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cand_a", help="Path to candidate A")
    parser.add_argument("cand_b", help="Path to candidate B")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--start_seed", type=int, default=0)
    args = parser.parse_args()
    benchmark_pairwise(args.cand_a, args.cand_b, num_seeds=args.seeds, start_seed=args.start_seed)
