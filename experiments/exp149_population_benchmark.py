"""EXP149 Multi-Process Population Benchmark Runner.

Evaluates D.1 Baseline Control across the full 10-archetype stratified population suite (200 total matches).
"""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

from benchmark.population_suite import POPULATION_SUITE

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

def main():
    print("=" * 145)
    print("EXP149: STRATIFIED KAGGLE REAL OPPONENT POPULATION BENCHMARK (10 ARCHETYPES / 200 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    # Split 10 keys across 5 workers (2 keys per worker)
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp149_worker.py"), chunk_str, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, chunk, worker_id))
        print(f"  Launched Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp149_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Stratified Scorecard by Archetype
    print("\n" + "=" * 145)
    print(f"{'Opponent Key':<24} | {'Tier':<25} | {'Archetype Description':<40} | {'D.1 WR':<8} | {'Mean Hero ($)':<14} | {'Mean Margin ($)'}")
    print("=" * 145)

    archetype_summaries = {}
    tier_groups = {}

    for b_key in all_keys:
        sub_items = [d for d in all_data if d["bot_key"] == b_key]
        n = len(sub_items)
        if n == 0: continue

        n_won = sum(1 for d in sub_items if d["won"])
        wr = (n_won / n) * 100
        mean_hero = float(np.mean([d["hero_reward"] for d in sub_items]))
        mean_opp = float(np.mean([d["opp_reward"] for d in sub_items]))
        mean_margin = float(np.mean([d["margin"] for d in sub_items]))
        tier = sub_items[0]["tier"]
        archetype = sub_items[0]["archetype"]

        archetype_summaries[b_key] = {
            "tier": tier, "archetype": archetype,
            "matches": n, "wins": n_won, "wr": wr,
            "mean_hero": mean_hero, "mean_opp": mean_opp, "mean_margin": mean_margin,
        }

        if tier not in tier_groups:
            tier_groups[tier] = []
        tier_groups[tier].extend(sub_items)

        print(f"{b_key:<24} | {tier:<25} | {archetype:<40} | {wr:5.1f}%  | ${mean_hero:12,.2f} | ${mean_margin:+13,.2f}")

    # 2. Stratified Scorecard by Tier
    print("\n" + "=" * 145)
    print(f"{'Tier Group':<30} | {'Total Matches':<14} | {'D.1 Win Rate':<14} | {'Mean Hero Reward ($)':<22} | {'Mean Margin ($)'}")
    print("=" * 145)

    tier_summaries = {}
    for tier_name, t_items in tier_groups.items():
        n_t = len(t_items)
        n_t_won = sum(1 for d in t_items if d["won"])
        t_wr = (n_t_won / n_t) * 100
        t_hero = float(np.mean([d["hero_reward"] for d in t_items]))
        t_margin = float(np.mean([d["margin"] for d in t_items]))

        tier_summaries[tier_name] = {
            "matches": n_t, "wins": n_t_won, "wr": t_wr,
            "mean_hero": t_hero, "mean_margin": t_margin,
        }

        print(f"{tier_name:<30} | {n_t:<14} | {t_wr:5.1f}%        | ${t_hero:18,.2f}   | ${t_margin:+13,.2f}")

    # Overall Summary
    total_n = len(all_data)
    total_wins = sum(1 for d in all_data if d["won"])
    overall_wr = (total_wins / total_n) * 100
    overall_hero = float(np.mean([d["hero_reward"] for d in all_data]))
    overall_margin = float(np.mean([d["margin"] for d in all_data]))

    print("-" * 145)
    print(f"{'OVERALL POPULATION BASKET':<30} | {total_n:<14} | {overall_wr:5.1f}%        | ${overall_hero:18,.2f}   | ${overall_margin:+13,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp149_population_benchmark_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "total_matches": total_n,
                "overall_wr": _to_native(overall_wr),
                "mean_hero_reward": _to_native(overall_hero),
                "mean_margin": _to_native(overall_margin),
            },
            "by_tier": _to_native(tier_summaries),
            "by_archetype": _to_native(archetype_summaries),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP149 Population Benchmark Results: {out_json}")

if __name__ == "__main__":
    main()
