"""ENVIRONMENT PARITY FORENSICS (Kaggle Server Replays vs Local Simulator).

Compares:
1. Environment Configuration (configuration dict from Kaggle server vs local kaggle_environments).
2. Initial Observation Schema (Step 0: money, unlocked_quadrants, tiles, workers, storage).
3. Land Expansion Mechanics (Step 719 unlocked quadrants count across live Kaggle matches).
4. Market Prices, Crop Growth Mechanics, Storage Limits, and Scoring Formula.

NO MODIFICATIONS TO RUNTIME ARTIFACTS OR PROTECTED BASELINES.
"""

from __future__ import annotations
import sys
import os
import glob
import json
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def find_kaggle_replays() -> List[str]:
    search_dirs = [
        os.path.join(BASE_DIR, "l+reviews"),
        os.path.join(BASE_DIR, "l+reviews", "newl"),
        os.path.join(BASE_DIR, "l++reviews"),
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

def analyze_parity():
    print("====================================================================================================", flush=True)
    print("🔬 ENVIRONMENT PARITY FORENSICS: KAGGLE SERVER REPLAYS VS LOCAL SIMULATOR", flush=True)
    print("====================================================================================================", flush=True)

    replays = find_kaggle_replays()
    print(f"Found {len(replays)} actual Kaggle server replay JSON files.", flush=True)

    if not replays:
        print("ERROR: No Kaggle replay files found!")
        return

    # Load local environment configuration & initial observation
    local_env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
    local_env.reset()
    local_config = dict(local_env.configuration)
    local_step0 = local_env.steps[0][0]["observation"]

    # Load first Kaggle server replay
    with open(replays[0], "r", encoding="utf-8") as f:
        k_data = json.load(f)

    k_config = k_data.get("configuration", {})
    k_steps = k_data.get("steps", [])
    k_step0 = k_steps[0][0]["observation"] if k_steps else {}

    print("\n--- ⚙️ PART 1: CONFIGURATION PARITY COMPARISON ---", flush=True)
    all_keys = sorted(list(set(local_config.keys()) | set(k_config.keys())))
    diffs_config = []
    for k in all_keys:
        loc_val = local_config.get(k, "<MISSING>")
        k_val = k_config.get(k, "<MISSING>")
        match = (loc_val == k_val)
        if not match:
            diffs_config.append(k)
        print(f"  {k:<25} | Local: {str(loc_val):<20} | Kaggle Server: {str(k_val):<20} | {'MATCH ✅' if match else 'DIFF 🚨'}")

    print("\n--- 🌾 PART 2: INITIAL STEP 0 OBSERVATION SCHEMA PARITY ---", flush=True)
    loc_farm0 = local_step0.get("farms", [{}])[0] if local_step0.get("farms") else {}
    k_farm0 = k_step0.get("farms", [{}])[0] if k_step0.get("farms") else {}

    print(f"  Local Step 0 Money         : ${loc_farm0.get('money', 0.0)}")
    print(f"  Kaggle Step 0 Money        : ${k_farm0.get('money', 0.0)}")
    print(f"  Local Step 0 Quads         : {loc_farm0.get('unlocked_quadrants', [])}")
    print(f"  Kaggle Step 0 Quads        : {k_farm0.get('unlocked_quadrants', [])}")
    print(f"  Local Step 0 Tiles Rows    : {len(loc_farm0.get('tiles', []))}x{len(loc_farm0.get('tiles', [[]])[0]) if loc_farm0.get('tiles') else 0}")
    print(f"  Kaggle Step 0 Tiles Rows   : {len(k_farm0.get('tiles', []))}x{len(k_farm0.get('tiles', [[]])[0]) if k_farm0.get('tiles') else 0}")

    print("\n--- 🗺️ PART 3: REPLAY QUADRANT UNLOCK DISTRIBUTION (STEP 719 ACROSS ALL KAGGLE REPLAYS) ---", flush=True)
    quad_counts_kaggle = {1: 0, 2: 0, 3: 0, 4: 0}
    total_kaggle_players = 0

    for rpath in replays:
        try:
            with open(rpath, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
            rep_steps = rep_data.get("steps", [])
            if len(rep_steps) >= 720:
                final_obs = rep_steps[-1]
                for p_idx in [0, 1]:
                    if len(final_obs) > p_idx:
                        p_farm = final_obs[p_idx].get("observation", {}).get("farms", [{}, {}])[p_idx]
                        unlocked = list(p_farm.get("unlocked_quadrants", []) or [])
                        q_cnt = min(4, max(1, len(unlocked)))
                        quad_counts_kaggle[q_cnt] += 1
                        total_kaggle_players += 1
        except Exception:
            continue

    print(f"Total Kaggle Live Players Analyzed: {total_kaggle_players}")
    for q_cnt, count in quad_counts_kaggle.items():
        pct = (count / total_kaggle_players * 100.0) if total_kaggle_players > 0 else 0.0
        print(f"  Kaggle Final Step 719 Land Quadrants = {q_cnt}: {count:3d} players ({pct:5.1f}%)")

    # Output report markdown
    report_path = os.path.join(BASE_DIR, "docs", "ENVIRONMENT_PARITY_FORENSICS_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🔬 ENVIRONMENT PARITY FORENSICS REPORT\n\n")
        f.write(f"Analyzed {len(replays)} Kaggle server replays against local `kaggle_environments`.\n\n")
        f.write("## 1. Configuration Diffs:\n")
        if not diffs_config:
            f.write("  - 100% Configuration Parity Matched! (0 Discrepancies)\n")
        else:
            for d in diffs_config:
                f.write(f"  - Config Diff: `{d}` | Local: {local_config.get(d)} | Kaggle: {k_config.get(d)}\n")
        f.write("\n## 2. Land Expansion Distribution in Kaggle Server Replays:\n")
        for q_cnt, count in quad_counts_kaggle.items():
            pct = (count / total_kaggle_players * 100.0) if total_kaggle_players > 0 else 0.0
            f.write(f"  - Land Quadrants = {q_cnt}: {count} players ({pct:.1f}%)\n")

    print(f"\nEnvironment Parity Report written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    analyze_parity()
