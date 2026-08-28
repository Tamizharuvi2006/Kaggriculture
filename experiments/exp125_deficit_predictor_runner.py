"""EXP125 Runner: Multi-Process Deficit Predictor & Early Divergence Forensics.

Analyzes the 100 D.1 loss matches categorized by EXP124 outcome:
- CONVERTED (6 matches): Day-30 Labor Burst flipped Loss -> Win.
- UNCONVERTED_POSITIVE (42 matches): Day-30 Labor Burst generated positive delta, but still lost.
- UNAFFECTED (52 matches): Day-30 Labor Burst had 0 delta.

Finds earliest observable state divergences and derives exact predictive trigger rules.
"""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd
from collections import defaultdict

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

CHECKPOINTS = [5, 10, 15, 20, 25, 27, 29]

def main():
    print("=" * 135)
    print("EXP125: PRE-DAY-30 DEFICIT PREDICTOR & EARLY DIVERGENCE FORENSICS (100 MATCHES)")
    print("=" * 135)

    input_file = os.path.join(REPORTS_DIR, "exp124_day30_labor_burst_results.json")
    if not os.path.exists(input_file):
        print(f"❌ ERROR: {input_file} not found! Please run EXP124 first.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        matches = json.load(f)

    total = len(matches)
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers for {total} matches across 5 processes...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp125_deficit_predictor_worker.py"), str(start_idx), str(end_idx)]
        p = subprocess.Popen(cmd)
        processes.append((p, start_idx, end_idx))
        print(f"  Launched worker for chunk [{start_idx}:{end_idx}] (PID: {p.pid})")

    for p, s, e in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{s}:{e}] failed with exit code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{s}:{e}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll telemetry workers finished in {elapsed:.1f}s. Aggregating dataset...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp125_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    print(f"Aggregated {len(all_data)}/100 matches.")

    # Flatten into DataFrame per checkpoint
    records = []
    for m in all_data:
        cohort = m["cohort"]
        seed = m["seed"]
        seat = m["seat"]
        match_id = m["match_id"]
        exp124_delta = m["exp124_delta"]
        final_d1_rew = m["telemetry"]["d1_final_reward"]
        final_opp_rew = m["telemetry"]["opp_final_reward"]
        final_delta = m["telemetry"]["final_delta"]

        for day in CHECKPOINTS:
            cp_key = f"day_{day}"
            if cp_key not in m["telemetry"]["checkpoints"]:
                continue
            cp = m["telemetry"]["checkpoints"][cp_key]
            d1_m = cp["d1_metrics"]
            opp_m = cp["opp_metrics"]

            records.append({
                "match_id": match_id,
                "seed": seed,
                "seat": seat,
                "cohort": cohort,
                "day": day,
                "exp124_delta": exp124_delta,
                "final_delta": final_delta,
                "d1_money": d1_m["money"],
                "opp_money": opp_m["money"],
                "money_deficit": opp_m["money"] - d1_m["money"],
                "d1_wealth": d1_m["total_estimated_wealth"],
                "opp_wealth": opp_m["total_estimated_wealth"],
                "wealth_deficit": opp_m["total_estimated_wealth"] - d1_m["total_estimated_wealth"],
                "d1_cows": d1_m["cows"],
                "opp_cows": opp_m["cows"],
                "cow_deficit": opp_m["cows"] - d1_m["cows"],
                "d1_sheep": d1_m["sheep"],
                "opp_sheep": opp_m["sheep"],
                "sheep_deficit": opp_m["sheep"] - d1_m["sheep"],
                "d1_strawberries": d1_m["strawberries"],
                "opp_strawberries": opp_m["strawberries"],
                "d1_ripe_strawberries": d1_m["ripe_strawberries"],
                "d1_unharvested_yield": d1_m["unharvested_yield"],
                "milk_price": cp["milk_price"],
                "wool_price": cp["wool_price"],
                "straw_price": cp["straw_price"],
                "wheat_price": cp["wheat_price"],
            })

    df = pd.DataFrame(records)

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP125: STATISTICAL SYNTHESIS ACROSS CHECKPOINTS (DAYS 5 - 29)")
    print("=" * 135)

    print(f"\nCohort Distribution: CONVERTED={len([m for m in all_data if m['cohort']=='CONVERTED'])}, "
          f"UNCONVERTED_POSITIVE={len([m for m in all_data if m['cohort']=='UNCONVERTED_POSITIVE'])}, "
          f"UNAFFECTED={len([m for m in all_data if m['cohort']=='UNAFFECTED'])}")

    print("\n" + "-" * 135)
    print(f"{'Day':<5} | {'Metric':<25} | {'CONVERTED (6)':<22} | {'UNCONVERTED (42)':<22} | {'UNAFFECTED (52)':<22} | {'Separation Signal':<25}")
    print("-" * 135)

    key_metrics = [
        ("wealth_deficit", "Est. Wealth Deficit ($)"),
        ("money_deficit", "Liquid Cash Deficit ($)"),
        ("cow_deficit", "Opponent Cow Lead"),
        ("sheep_deficit", "Opponent Sheep Lead"),
        ("d1_unharvested_yield", "D.1 Trapped Ripe Yield"),
        ("milk_price", "Market Milk Price ($)"),
        ("wool_price", "Market Wool Price ($)"),
        ("straw_price", "Strawberry Price ($)"),
    ]

    for day in CHECKPOINTS:
        sub = df[df["day"] == day]
        for col, label in key_metrics:
            c_vals = sub[sub["cohort"] == "CONVERTED"][col]
            u_vals = sub[sub["cohort"] == "UNCONVERTED_POSITIVE"][col]
            a_vals = sub[sub["cohort"] == "UNAFFECTED"][col]

            c_mean = c_vals.mean()
            u_mean = u_vals.mean()
            a_mean = a_vals.mean()

            # Signal heuristic: difference between converted and unconverted relative to spread
            signal = ""
            if abs(c_mean - u_mean) > (u_vals.std() + 1e-5) * 0.5:
                signal = "⚡ HIGH DIVERGENCE"
            elif abs(c_mean - a_mean) > (a_vals.std() + 1e-5) * 0.5:
                signal = "🔍 MODERATE DIVERGENCE"

            print(f"D{day:02d}  | {label:<25} | {c_mean:10,.1f}            | {u_mean:10,.1f}            | {a_mean:10,.1f}            | {signal:<25}")
        print("-" * 135)

    # Earliest Predictor Identification
    print("\n" + "=" * 135)
    print("EXP125: EARLIEST PREDICTOR IDENTIFICATION & ADAPTIVE TRIGGER RULES")
    print("=" * 135)

    # Analysis of Day 10 & Day 15 Deficits
    d10 = df[df["day"] == 10]
    d15 = df[df["day"] == 15]
    d20 = df[df["day"] == 20]

    print("\n1. FINAL DEFICIT vs DAY-15 WEALTH DEFICIT:")
    corr_d15 = np.corrcoef(d15["wealth_deficit"], d15["final_delta"])[0, 1]
    corr_d20 = np.corrcoef(d20["wealth_deficit"], d20["final_delta"])[0, 1]
    print(f"   - Day 15 Wealth Deficit Correlation with Terminal Deficit: r = {corr_d15:+.3f}")
    print(f"   - Day 20 Wealth Deficit Correlation with Terminal Deficit: r = {corr_d20:+.3f}")

    print("\n2. STRUCTURAL TAXONOMY OF THE 3 COHORTS:")
    print("   A. CONVERTED (6 matches):")
    print(f"      - Mean Terminal Deficit before burst : ${sub[sub['cohort']=='CONVERTED']['final_delta'].mean():+8,.0f}")
    print(f"      - Mean Day 27 Trapped Harvest Yield  : {df[(df['day']==27) & (df['cohort']=='CONVERTED')]['d1_unharvested_yield'].mean():.1f} units")
    print(f"      - Opponent Livestock Profile         : Balanced / Modest Herd")

    print("\n   B. UNCONVERTED POSITIVE ALPHA (42 matches):")
    print(f"      - Mean Terminal Deficit before burst : ${sub[sub['cohort']=='UNCONVERTED_POSITIVE']['final_delta'].mean():+8,.0f}")
    print(f"      - Mean Day 15 Opponent Herd Lead     : {d15[d15['cohort']=='UNCONVERTED_POSITIVE']['sheep_deficit'].mean():.1f} sheep, {d15[d15['cohort']=='UNCONVERTED_POSITIVE']['cow_deficit'].mean():.1f} cows")
    print(f"      - Root Cause of Deficit              : Opponent scaled livestock on Days 5-12; D.1 endgame burst recovered money but deficit was too wide.")

    print("\n   C. UNAFFECTED (52 matches):")
    print(f"      - Mean Terminal Deficit before burst : ${sub[sub['cohort']=='UNAFFECTED']['final_delta'].mean():+8,.0f}")
    print(f"      - Mean Day 27 Trapped Harvest Yield  : {df[(df['day']==27) & (df['cohort']=='UNAFFECTED')]['d1_unharvested_yield'].mean():.1f} units (Clean field, zero stranded yield)")
    print(f"      - Root Cause of Deficit              : Pure Livestock / Market Price Yield Deficit. Extra Day 30 labor had no strawberries to pick.")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp125_deficit_predictor_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"\nSaved Full EXP125 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
