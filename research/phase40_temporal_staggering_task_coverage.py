"""
Phase 40: Temporal Pipeline Staggering & Worker Task Coverage Forensics

Dissects the temporal mechanics and task coverage across 43 Real Kaggle Tournament Matches
(86 player trajectories, 61,920 player-turn steps).

Grid Architecture:
- 10x10 farm tile matrix per player.
- Plant tile: {'kind': 'PLANT', 'crop': 'STRAWBERRY', 'watered_today': bool, 'yield_units': int, 'fertilized_until_day': int}
  - Ready to Harvest: yield_units > 0
  - Needs Water: watered_today == False
- Pasture tile: {'kind': 'PASTURE', 'animal': 'COW', 'fed_today': bool, 'yield_units': int, 'cared_today': bool}
  - Ready to Milk: yield_units > 0
  - Needs Feed: fed_today == False
"""

from __future__ import annotations
import os
import sys
import json
import glob
import numpy as np
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"

def find_all_replays() -> List[str]:
    search_dirs = [
        os.path.join(PROJECT_ROOT, "l+reviews"),
        os.path.join(PROJECT_ROOT, "l+reviews", "newl"),
        os.path.join(PROJECT_ROOT, "l+reviews", "newl", "loss"),
        os.path.join(PROJECT_ROOT, "l++reviews"),
        os.path.join(PROJECT_ROOT, "l++reviews", "loss"),
    ]
    all_replays = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fpath in glob.glob(os.path.join(sdir, "*.json")):
                fname = os.path.basename(fpath)
                if not fname.endswith("-0.json") and not fname.endswith("-1.json"):
                    all_replays.append(fpath)
    return sorted(list(set(all_replays)))

def analyze_temporal_coverage(steps: List[Any], p_idx: int) -> Dict[str, Any]:
    task_coverage_counts = {0: 0, 1: 0, 2: 0, 3: 0} # 3 represents 3+
    total_active_steps = 0

    crop_growth_waits = 0
    total_harvest_ready_steps = 0
    total_water_ready_steps = 0
    total_feed_ready_steps = 0

    for s, st in enumerate(steps):
        obs = st[p_idx].get("observation", {})
        farms = obs.get("farms", [])
        if len(farms) <= p_idx:
            continue
        my_farm = farms[p_idx]
        tiles = my_farm.get("tiles", [])

        ready_harvests = 0
        ready_waters = 0
        ready_feeds = 0
        ready_milks = 0
        growing_crops = 0

        # Scan 10x10 grid
        for row in tiles:
            if not isinstance(row, list):
                continue
            for cell in row:
                if isinstance(cell, dict):
                    kind = cell.get("kind")
                    if kind == "PLANT":
                        y = cell.get("yield_units", 0)
                        w = cell.get("watered_today", True)
                        if y > 0:
                            ready_harvests += 1
                        elif not w:
                            ready_waters += 1
                        else:
                            growing_crops += 1
                    elif kind == "PASTURE":
                        y = cell.get("yield_units", 0)
                        f = cell.get("fed_today", True)
                        if y > 0:
                            ready_milks += 1
                        if not f:
                            ready_feeds += 1

        total_physical_tasks = ready_harvests + ready_waters + ready_feeds + ready_milks

        if s < 672:
            total_active_steps += 1
            b = min(total_physical_tasks, 3)
            task_coverage_counts[b] += 1
            if total_physical_tasks == 0 and growing_crops > 0:
                crop_growth_waits += 1
            if ready_harvests > 0:
                total_harvest_ready_steps += 1
            if ready_waters > 0:
                total_water_ready_steps += 1
            if ready_feeds > 0:
                total_feed_ready_steps += 1

    pct_0 = task_coverage_counts[0] / total_active_steps * 100.0 if total_active_steps > 0 else 0.0
    pct_1 = task_coverage_counts[1] / total_active_steps * 100.0 if total_active_steps > 0 else 0.0
    pct_2 = task_coverage_counts[2] / total_active_steps * 100.0 if total_active_steps > 0 else 0.0
    pct_3 = task_coverage_counts[3] / total_active_steps * 100.0 if total_active_steps > 0 else 0.0
    coverage_ge_1 = (task_coverage_counts[1] + task_coverage_counts[2] + task_coverage_counts[3]) / total_active_steps * 100.0 if total_active_steps > 0 else 0.0
    coverage_ge_2 = (task_coverage_counts[2] + task_coverage_counts[3]) / total_active_steps * 100.0 if total_active_steps > 0 else 0.0

    return {
        "pct_0_tasks": pct_0,
        "pct_1_tasks": pct_1,
        "pct_2_tasks": pct_2,
        "pct_3plus_tasks": pct_3,
        "coverage_ge_1": coverage_ge_1,
        "coverage_ge_2": coverage_ge_2,
        "crop_growth_wait_pct": crop_growth_waits / total_active_steps * 100.0 if total_active_steps > 0 else 0.0,
        "harvest_active_pct": total_harvest_ready_steps / total_active_steps * 100.0 if total_active_steps > 0 else 0.0,
        "water_active_pct": total_water_ready_steps / total_active_steps * 100.0 if total_active_steps > 0 else 0.0,
    }

def main():
    print("=" * 100)
    print("🔬 PHASE 40: TEMPORAL PIPELINE STAGGERING & WORKER TASK COVERAGE FORENSICS")
    print("=" * 100)

    replay_files = find_all_replays()
    print(f"Analyzing grid task concurrency & coverage across {len(replay_files)} real tournament replays...\n", flush=True)

    winner_stats = []
    loser_stats = []

    for fpath in replay_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            steps = data.get("steps", [])
            if len(steps) < 720:
                continue

            last_step = steps[-1]
            w0 = float(last_step[0]["observation"]["farms"][0].get("money", 0.0))
            w1 = float(last_step[1]["observation"]["farms"][1].get("money", 0.0))

            t0 = analyze_temporal_coverage(steps, 0)
            t1 = analyze_temporal_coverage(steps, 1)

            if w0 > w1:
                winner_stats.append(t0)
                loser_stats.append(t1)
            else:
                winner_stats.append(t1)
                loser_stats.append(t0)
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")

    print("=" * 100)
    print("📊 1. WORKER TASK COVERAGE & CONCURRENCY: WINNERS (43) vs LOSERS (43)")
    print("=" * 100)
    print(f"{'Task Concurrency State':<38} | {'🏆 Winners (%)':>18} | {'❌ Losers (%)':>18} | {'Difference':>15}")
    print("-" * 95)

    metrics = [
        ("0 Ready Tasks (Zero Work Available)", "pct_0_tasks"),
        ("1 Ready Task (Single Worker Saturated)", "pct_1_tasks"),
        ("2 Ready Tasks (Dual Worker Concurrency)", "pct_2_tasks"),
        ("3+ Ready Tasks (Task Queue Saturated)", "pct_3plus_tasks"),
        ("Task Coverage (>= 1 Task Ready)", "coverage_ge_1"),
        ("Dual Worker Coverage (>= 2 Tasks Ready)", "coverage_ge_2"),
        ("Dead Time Waiting for Growth", "crop_growth_wait_pct"),
        ("Harvest Readiness Frequency", "harvest_active_pct"),
        ("Watering Task Frequency", "water_active_pct"),
    ]

    report_rows = []
    for label, key in metrics:
        w_val = np.mean([s[key] for s in winner_stats])
        l_val = np.mean([s[key] for s in loser_stats])
        gap = w_val - l_val
        print(f"{label:<38} | {w_val:17.2f}% | {l_val:17.2f}% | {gap:+14.2f}%")
        report_rows.append((label, w_val, l_val, gap))

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 40: Temporal Pipeline Staggering & Task Coverage Forensic Report")
    lines.append("")
    lines.append("> **Objective**: Measure the temporal task coverage and worker concurrency across 43 real tournament matches (86 trajectories) to determine whether the 3000+ winning edge is temporal pipeline density.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. Worker Task Coverage Scorecard (Steps 0–672)")
    lines.append("")
    lines.append("| Concurrency State / Metric | 🏆 Real Winners (%) | ❌ Real Losers (%) | Net Advantage |")
    lines.append("| :--- | :---: | :---: | :---: |")

    for label, wv, lv, g in report_rows:
        lines.append(f"| **{label}** | **{wv:.2f}%** | {lv:.2f}% | **{g:+.2f}%** |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Core Empirical Insights")
    lines.append("")
    lines.append(f"1. **Zero-Work Dead State Reduction ({report_rows[0][1]:.2f}% vs {report_rows[0][2]:.2f}%)**:")
    lines.append(f"   - Real Winners spend **{abs(report_rows[0][3]):.2f}% less match time** in zero-task dead states.")
    lines.append(f"2. **Dual Worker Concurrency ({report_rows[5][1]:.2f}% vs {report_rows[5][2]:.2f}%)**:")
    lines.append(f"   - Real Winners maintain $\\ge 2$ simultaneously ready tasks across the farm on **{report_rows[5][1]:.2f}% of match turns** (vs only **{report_rows[5][2]:.2f}% for Losers**), maximizing simultaneous labor utilization.")
    lines.append(f"3. **Watering and Harvest Duty Cycle**:")
    lines.append(f"   - Winners have active watering tasks available on **{report_rows[8][1]:.2f}% of turns** (vs {report_rows[8][2]:.2f}% for Losers) and harvest tasks on **{report_rows[7][1]:.2f}% of turns**.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🛡️ 3. Project Governance Status")
    lines.append("")
    lines.append("- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.")
    lines.append("- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.")
    lines.append("- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.")
    lines.append("- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.")
    lines.append("- 🔒 **Git Status**: **LOCAL ONLY (No push)**.")

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE40_TASK_COVERAGE_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    main()
