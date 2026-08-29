"""EXP153 Multi-Process Runner: Forensic Mining of Steps 216-695 across 20 V18 Mirror Matches."""
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
    print("EXP153: PRE-DAY-30 MIRROR ACTION-LEVEL CAUSAL MINING (STEPS 216-695 / 20 MATCHES)")
    print("=" * 145)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    # Split 20 seeds across 5 parallel workers (4 seeds per worker)
    chunks = [seeds[i:i+4] for i in range(0, len(seeds), 4)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(str(s) for s in chunk)
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp153_worker.py"), chunk_str, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, chunk, worker_id))
        print(f"  Launched Worker {idx} for seeds: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating action logs...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp153_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Forensic Action Audit Summary
    print("\n" + "=" * 145)
    print("TOP PRE-DAY-30 ACTION DIVERGENCES (D.1 HERO VS V18 OPPONENT):")
    print("=" * 145)

    # Seed Purchases
    h_straw_seeds = np.mean([d["h_seed_buys"]["STRAWBERRY"] for d in all_data])
    o_straw_seeds = np.mean([d["o_seed_buys"]["STRAWBERRY"] for d in all_data])
    h_carrot_seeds = np.mean([d["h_seed_buys"]["CARROT"] for d in all_data])
    o_carrot_seeds = np.mean([d["o_seed_buys"]["CARROT"] for d in all_data])

    # Late Game Plantings (Day 26+ / Step 624-695)
    h_late_straw = np.mean([d["h_plants_late"]["STRAWBERRY"] for d in all_data])
    o_late_straw = np.mean([d["o_plants_late"]["STRAWBERRY"] for d in all_data])
    h_late_carrot = np.mean([d["h_plants_late"]["CARROT"] for d in all_data])
    o_late_carrot = np.mean([d["o_plants_late"]["CARROT"] for d in all_data])

    # Animal Feeding
    h_feed = np.mean([d["h_feed_cows"] for d in all_data])
    o_feed = np.mean([d["o_feed_cows"] for d in all_data])

    # Market Transaction Frequency
    h_sells = np.mean([d["h_sell_count"] for d in all_data])
    o_sells = np.mean([d["o_sell_count"] for d in all_data])

    print(f"1. Late-Game Strawberry Plantings (Day 26+ / Step 624-695):")
    print(f"   D.1 Plants = {h_late_straw:5.1f} tiles  |  V18 Plants = {o_late_straw:5.1f} tiles  (Delta: {h_late_straw - o_late_straw:+5.1f} tiles)")
    print(f"   * CRITICAL: Strawberries planted on Day 28+ (Steps 672-695) cost $25/seed but CANNOT mature before Step 720!")

    print(f"\n2. Total Strawberry Seeds Purchased (Steps 216-695):")
    print(f"   D.1 Purchased = {h_straw_seeds:5.1f} seeds  |  V18 Purchased = {o_straw_seeds:5.1f} seeds  (Delta: {h_straw_seeds - o_straw_seeds:+5.1f} seeds)")

    print(f"\n3. Total Carrot Seeds Purchased / Planted (Steps 216-695):")
    print(f"   D.1 Carrots = {h_carrot_seeds:5.1f} seeds  |  V18 Carrots = {o_carrot_seeds:5.1f} seeds  (Delta: {h_carrot_seeds - o_carrot_seeds:+5.1f} seeds)")

    print(f"\n4. Animal Feeding Frequency (FEED actions during Steps 216-695):")
    print(f"   D.1 FEED = {h_feed:5.1f} actions  |  V18 FEED = {o_feed:5.1f} actions  (Delta: {h_feed - o_feed:+5.1f} actions)")

    print(f"\n5. Market Sell Transaction Cadence (Sell order frequency Steps 216-695):")
    print(f"   D.1 Sells = {h_sells:5.1f} orders  |  V18 Sells = {o_sells:5.1f} orders  (Delta: {h_sells - o_sells:+5.1f} orders)")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp153_mirror_action_miner_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_matches": len(all_data),
            "h_late_straw": float(h_late_straw), "o_late_straw": float(o_late_straw),
            "h_straw_seeds": float(h_straw_seeds), "o_straw_seeds": float(o_straw_seeds),
            "h_feed": float(h_feed), "o_feed": float(o_feed),
            "h_sells": float(h_sells), "o_sells": float(o_sells),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP153 Action Miner Results: {out_json}")

if __name__ == "__main__":
    main()
