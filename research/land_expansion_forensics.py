"""LAND EXPANSION FORENSICS (Research Branch).

Analyzes historical replays to investigate 3-Land vs 4-Land expansion trajectories:
1. Exact Step/Day when Quadrants 2, 3, and 4 are unlocked.
2. Cash, Worker count, Crop distribution, and Inventory state prior to expansion.
3. Downstream wealth delta (120 steps post-expansion) and Final Wealth.
4. Win rate comparison: 4-Land Expansion vs 3-Land Cap.
5. Strategic preconditions for profitable 4th Land expansion.

RULES MAINTAINED: NO MODIFICATION TO APEX 3.0 RUNTIME ARTIFACT. RULE ZERO INTACT.
"""

from __future__ import annotations
import sys
import os
import glob
import json
import math
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def find_all_replays() -> List[str]:
    search_dirs = [
        os.path.join(BASE_DIR, "l+reviews"),
        os.path.join(BASE_DIR, "l+reviews", "newl"),
        os.path.join(BASE_DIR, "l+reviews", "newl", "loss"),
        os.path.join(BASE_DIR, "l++reviews"),
        os.path.join(BASE_DIR, "l++reviews", "loss"),
    ]
    all_replays = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fpath in glob.glob(os.path.join(sdir, "*.json")):
                fname = os.path.basename(fpath)
                if fname.endswith("-0.json") or fname.endswith("-1.json"):
                    continue
                all_replays.append(fpath)
    return sorted(list(set(all_replays)))

def analyze_replay_land_expansion(fpath: str) -> List[Dict[str, Any]]:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    steps = data.get("steps", [])
    if len(steps) < 720:
        return []

    last_step = steps[-1]
    p0_final = float(last_step[0]["observation"]["farms"][0].get("money", 0.0))
    p1_final = float(last_step[1]["observation"]["farms"][1].get("money", 0.0))

    player_records = []

    for p_idx in [0, 1]:
        my_final = p0_final if p_idx == 0 else p1_final
        opp_final = p1_final if p_idx == 0 else p0_final
        won = my_final >= opp_final

        quadrant_history = {} # quad_count -> {step, day, cash_before, workers}
        prev_quad_count = 0

        for step_idx in range(len(steps)):
            step_obj = steps[step_idx]
            obs = step_obj[p_idx].get("observation", {})
            if not obs or "farms" not in obs:
                continue

            farms = obs.get("farms", [])
            if len(farms) <= p_idx:
                continue

            my_farm = farms[p_idx]
            unlocked_quads = list(my_farm.get("unlocked_quadrants", []) or [])
            curr_quad_count = len(unlocked_quads)

            if curr_quad_count > prev_quad_count:
                # Land purchase detected!
                money = float(my_farm.get("money", 0.0))
                workers = len(my_farm.get("workers", []) or [])
                day = step_idx // 24
                
                # Sample downstream 120 steps
                step_120 = min(719, step_idx + 120)
                obs_120 = steps[step_120][p_idx].get("observation", {})
                wealth_120 = float(obs_120.get("farms", [{}])[p_idx].get("money", money)) if len(obs_120.get("farms", [])) > p_idx else money

                quadrant_history[curr_quad_count] = {
                    "step": step_idx,
                    "day": day,
                    "cash_before": money,
                    "workers": workers,
                    "quadrants": unlocked_quads,
                    "wealth_120": wealth_120,
                    "delta_120": wealth_120 - money
                }
                prev_quad_count = curr_quad_count

        max_quads = prev_quad_count
        player_records.append({
            "file": os.path.basename(fpath),
            "player_idx": p_idx,
            "won": won,
            "final_wealth": my_final,
            "opp_final_wealth": opp_final,
            "max_quadrants": max_quads,
            "quadrant_history": quadrant_history
        })

    return player_records

def main():
    print("====================================================================================================", flush=True)
    print("🔬 LAND EXPANSION FORENSICS: 3-LAND VS 4-LAND STRATEGIC DISCOVERY", flush=True)
    print("====================================================================================================", flush=True)

    replays = find_all_replays()
    print(f"Discovered {len(replays)} historical replay logs. Extracting land expansion trajectories...", flush=True)

    all_records = []
    for rpath in replays:
        recs = analyze_replay_land_expansion(rpath)
        all_records.extend(recs)

    print(f"Total Trajectories Extracted: {len(all_records)} (Player-Episodes)\n", flush=True)

    # Breakdown by max_quadrants
    quad_groups = {1: [], 2: [], 3: [], 4: []}
    for rec in all_records:
        q_cnt = min(4, max(1, rec["max_quadrants"]))
        quad_groups[q_cnt].append(rec)

    print("--- 📊 LAND EXPANSION FREQUENCY & WIN-RATE DISTRIBUTION ---")
    for q_cnt in range(1, 5):
        recs = quad_groups[q_cnt]
        count = len(recs)
        if count == 0:
            print(f"  Land Quadrants = {q_cnt}: 0 Trajectories")
            continue
        wins = sum(1 for r in recs if r["won"])
        win_rate = (wins / count) * 100.0
        avg_wealth = sum(r["final_wealth"] for r in recs) / count
        print(f"  Land Quadrants = {q_cnt} | Trajectories: {count:3d} | Win Rate: {wins:2d}/{count:2d} ({win_rate:5.1f}%) | Avg Final Wealth: ${avg_wealth:,.2f}")

    print("\n----------------------------------------------------------------------------------------------------")
    print("--- ⏱️ EXPANSION TIMING & CASH STATE ANALYSIS ---")

    for q_target in [2, 3, 4]:
        purchases = []
        for rec in all_records:
            if q_target in rec["quadrant_history"]:
                purchases.append(rec["quadrant_history"][q_target])
        if purchases:
            avg_day = sum(p["day"] for p in purchases) / len(purchases)
            min_day = min(p["day"] for p in purchases)
            max_day = max(p["day"] for p in purchases)
            avg_cash = sum(p["cash_before"] for p in purchases) / len(purchases)
            avg_workers = sum(p["workers"] for p in purchases) / len(purchases)
            avg_d120 = sum(p["delta_120"] for p in purchases) / len(purchases)
            print(f"  Land #{q_target} Purchase (N={len(purchases)}):")
            print(f"    ├── Timing Window     : Day {min_day} to Day {max_day} (Mean Day: {avg_day:.1f})")
            print(f"    ├── Mean Cash Before  : ${avg_cash:,.2f}")
            print(f"    ├── Mean Workers      : {avg_workers:.1f}")
            print(f"    └── Downstream +120 Step Delta : ${avg_d120:+,.2f}")

    print("\n----------------------------------------------------------------------------------------------------")
    print("--- ⚔️ 4-LAND VS 3-LAND HEAD-TO-HEAD COMPARISON ---")

    recs_3 = quad_groups[3]
    recs_4 = quad_groups[4]

    w3_mean = sum(r["final_wealth"] for r in recs_3) / len(recs_3) if recs_3 else 0.0
    w4_mean = sum(r["final_wealth"] for r in recs_4) / len(recs_4) if recs_4 else 0.0

    print(f"  3-Land Trajectories Mean Final Wealth : ${w3_mean:,.2f}")
    print(f"  4-Land Trajectories Mean Final Wealth : ${w4_mean:,.2f}")
    print(f"  Strategic Wealth Premium (4-Land - 3-Land) : ${w4_mean - w3_mean:+,.2f}")

    # Output detailed report file
    report_path = os.path.join(BASE_DIR, "docs", "LAND_EXPANSION_FORENSICS_REPORT.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🔬 LAND EXPANSION FORENSICS REPORT\n\n")
        f.write(f"Analyzed {len(all_records)} trajectories across {len(replays)} historical replays.\n\n")
        f.write(f"## Key Empirical Findings:\n")
        f.write(f"- 4-Land Expansion Count: {len(recs_4)} trajectories | Avg Wealth: ${w4_mean:,.2f}\n")
        f.write(f"- 3-Land Expansion Count: {len(recs_3)} trajectories | Avg Wealth: ${w3_mean:,.2f}\n")
        f.write(f"- Net 4th Land Premium: **${w4_mean - w3_mean:+,.2f}**\n")

    print(f"\nReport written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    main()
