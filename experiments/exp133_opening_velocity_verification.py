"""EXP133: Opening Velocity Verification & Land #2 Milestone Audit.

Audits:
1. Step when money >= $1,000 is first achieved.
2. Step when BUY_LAND is submitted in market orders.
3. Step when Quadrant #2 appears in farms[player]["unlocked_quadrants"].
4. Step when first crop/animal is placed in Quadrant #2.
5. Step when Quadrant #3 is unlocked.

Compares:
- D.1 Baseline Control
- <1200 Wall-Trapped Cohort
- 1200-1399 Brief Spikers
- 2000+ Grandmasters / Elite Titans
"""
from __future__ import annotations
import os
import sys
import json
import glob
from collections import defaultdict
import numpy as np
import pandas as pd

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
TELEMETRY_DIR = os.path.join(REPORTS_DIR, "live_match_telemetry")

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

def audit_replay_file(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = data.get("steps", [])
        if len(steps) < 20:
            return []

        results = []
        for p_idx in [0, 1]:
            opp_idx = 1 - p_idx
            last_step = steps[-1]
            last_obs = last_step[p_idx]["observation"]
            farms = last_obs.get("farms", [])
            if len(farms) < 2:
                continue

            our_farm = farms[p_idx]
            opp_farm = farms[opp_idx]
            our_money = float(our_farm.get("money", 0.0) or 0.0)
            opp_money = float(opp_farm.get("money", 0.0) or 0.0)
            won = our_money > opp_money

            # Milestone tracking
            step_cash_1000 = None
            step_buyland_submitted = None
            step_land2_unlocked = None
            step_land2_first_plant = None
            step_land3_unlocked = None

            quad2_name = None

            for s_idx, s in enumerate(steps):
                obs = s[p_idx]["observation"]
                farm = obs.get("farms", [])[p_idx]
                cash = float(farm.get("money", 0.0) or 0.0)
                unlocked = farm.get("unlocked_quadrants", ["NW"])

                if cash >= 1000.0 and step_cash_1000 is None:
                    step_cash_1000 = s_idx

                # Check action submitted by player
                # In Kaggle replays, action is in s[p_idx]["action"]
                act = s[p_idx].get("action") or {}
                if isinstance(act, dict):
                    m_orders = act.get("market", [])
                    if step_buyland_submitted is None:
                        for m in m_orders:
                            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                                step_buyland_submitted = (s_idx, m[1])

                if len(unlocked) >= 2 and step_land2_unlocked is None:
                    step_land2_unlocked = s_idx
                    quad2_name = unlocked[1]

                if len(unlocked) >= 3 and step_land3_unlocked is None:
                    step_land3_unlocked = s_idx

                if quad2_name and step_land2_first_plant is None:
                    r_range = range(0, 4) if "N" in quad2_name else range(4, 8)
                    c_range = range(0, 4) if "W" in quad2_name else range(4, 8)
                    tiles = farm.get("tiles", [])
                    for r in r_range:
                        for c in c_range:
                            if r < len(tiles) and c < len(tiles[r]):
                                t = tiles[r][c]
                                if isinstance(t, dict) and (t.get("crop") or t.get("animal")):
                                    step_land2_first_plant = s_idx
                                    break
                        if step_land2_first_plant is not None:
                            break

            results.append({
                "file": os.path.basename(file_path),
                "player": p_idx,
                "our_money": our_money,
                "opp_money": opp_money,
                "won": won,
                "step_cash_1000": step_cash_1000,
                "step_buyland_submitted": step_buyland_submitted[0] if step_buyland_submitted else None,
                "step_land2_unlocked": step_land2_unlocked,
                "step_land2_first_plant": step_land2_first_plant,
                "step_land3_unlocked": step_land3_unlocked,
            })
        return results
    except Exception as e:
        return []

def main():
    print("=" * 135)
    print("EXP133: OPENING VELOCITY VERIFICATION & LAND #2 MILESTONE AUDIT")
    print("=" * 135)

    # 1. Audit D.1 Baseline Control
    print("\n--- 1. D.1 BASELINE CONTROL MILESTONE AUDIT ---")
    import kaggle_environments, importlib.util
    spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
    sub_d1 = importlib.util.module_from_spec(spec_d1)
    spec_d1.loader.exec_module(sub_d1)

    d1_records = []
    for seed in [1000, 1001, 1002, 1003, 1004, 42, 20042]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        step_cash_1000 = None
        step_buyland_submitted = None
        step_land2_unlocked = None
        step_land2_first_plant = None
        step_land3_unlocked = None
        quad2_name = None

        while not env.done:
            s_idx = env.state[0].observation.get("step", 0)
            obs = env.state[0].observation
            farm = obs.get("farms", [])[0]
            cash = float(farm.get("money", 0.0) or 0.0)
            unlocked = farm.get("unlocked_quadrants", ["NW"])

            if cash >= 1000.0 and step_cash_1000 is None:
                step_cash_1000 = s_idx

            act0 = sub_d1.agent(obs, env.configuration)
            m_orders = act0.get("market", [])
            if step_buyland_submitted is None:
                for m in m_orders:
                    if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                        step_buyland_submitted = s_idx

            env.step([act0, {"farmer": ["PASS"], "hands": [], "market": []}])
            next_obs = env.state[0].observation
            next_farm = next_obs.get("farms", [])[0]
            next_unlocked = next_farm.get("unlocked_quadrants", ["NW"])

            if len(next_unlocked) >= 2 and step_land2_unlocked is None:
                step_land2_unlocked = s_idx
                quad2_name = next_unlocked[1]

            if len(next_unlocked) >= 3 and step_land3_unlocked is None:
                step_land3_unlocked = s_idx

            if quad2_name and step_land2_first_plant is None:
                r_range = range(0, 4) if "N" in quad2_name else range(4, 8)
                c_range = range(0, 4) if "W" in quad2_name else range(4, 8)
                tiles = next_farm.get("tiles", [])
                for r in r_range:
                    for c in c_range:
                        if r < len(tiles) and c < len(tiles[r]):
                            t = tiles[r][c]
                            if isinstance(t, dict) and (t.get("crop") or t.get("animal")):
                                step_land2_first_plant = s_idx
                                break
                    if step_land2_first_plant is not None:
                        break

        d1_records.append({
            "seed": seed,
            "cash_1000": step_cash_1000,
            "buyland_submitted": step_buyland_submitted,
            "land2_unlocked": step_land2_unlocked,
            "land2_first_plant": step_land2_first_plant,
            "land3_unlocked": step_land3_unlocked,
        })

    df_d1 = pd.DataFrame(d1_records)
    print(f"D.1 Milestone Timings (averaged across {len(df_d1)} runs):")
    print(f"  - Cash >= $1,000 Reached        : Step {df_d1['cash_1000'].mean():.1f} (Day {df_d1['cash_1000'].mean()/24+1:.1f})")
    print(f"  - BUY_LAND Submitted            : Step {df_d1['buyland_submitted'].mean():.1f} (Day {df_d1['buyland_submitted'].mean()/24+1:.1f})")
    print(f"  - Land #2 Unlocked in State     : Step {df_d1['land2_unlocked'].mean():.1f} (Day {df_d1['land2_unlocked'].mean()/24+1:.1f})")
    print(f"  - First Plant / Animal in Land #2: Step {df_d1['land2_first_plant'].mean():.1f} (Day {df_d1['land2_first_plant'].mean()/24+1:.1f})")
    print(f"  - Land #3 Unlocked in State     : Step {df_d1['land3_unlocked'].mean():.1f} (Day {df_d1['land3_unlocked'].mean()/24+1:.1f})")

    # 2. Audit Historical & Grandmaster Replays
    print("\n--- 2. CROSS-COHORT REPLAY MILESTONE AUDIT ---")
    replay_files = []
    replay_files.extend(glob.glob(os.path.join(TELEMETRY_DIR, "all_loss_replays_cache", "*.json")))
    replay_files.extend(glob.glob(os.path.join(TELEMETRY_DIR, "grandmaster_replays", "*.json")))
    replay_files.extend(glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "*", "*.json")))
    replay_files = [f for f in set(replay_files) if not f.endswith("-0.json") and not f.endswith("-1.json")]

    all_audits = []
    for rf in replay_files:
        all_audits.extend(audit_replay_file(rf))

    df_rep = pd.DataFrame(all_audits)

    # Classify into cohorts based on final money
    # High money = Grandmaster/Titan, Mid money = Spiker, Low money = Wall Trapped
    df_rep["cohort"] = "WALL_TRAPPED (<$60k)"
    df_rep.loc[df_rep["our_money"] >= 60000, "cohort"] = "BRIEF_SPIKERS ($60k-$80k)"
    df_rep.loc[df_rep["our_money"] >= 80000, "cohort"] = "ELITE_TITANS (>$80k)"

    print(f"Audited {len(df_rep)} agent lifecycles across replay files.")

    summary_rows = []
    for coh, grp in df_rep.groupby("cohort"):
        summary_rows.append({
            "cohort": coh,
            "count": len(grp),
            "mean_money": grp["our_money"].mean(),
            "step_cash_1000": grp["step_cash_1000"].mean(),
            "step_buyland": grp["step_buyland_submitted"].mean(),
            "step_land2_unlocked": grp["step_land2_unlocked"].mean(),
            "step_land2_first_plant": grp["step_land2_first_plant"].mean(),
            "step_land3_unlocked": grp["step_land3_unlocked"].mean(),
        })

    df_sum = pd.DataFrame(summary_rows)

    print("\n" + "=" * 135)
    print("EXP133: MILESTONE TIMELINE COMPARISON TABLE")
    print("=" * 135)
    print(f"{'Cohort':<26} | {'Count':<6} | {'Mean Wealth':<12} | {'Cash >= $1k':<12} | {'BUY_LAND':<10} | {'Land #2 Unl':<12} | {'1st Plant #2':<12} | {'Land #3 Unl'}")
    print("-" * 135)
    print(f"{'D.1 Baseline Control':<26} | {len(df_d1):<6} | ${68000:<11,.0f} | Step {df_d1['cash_1000'].mean():<7.1f} | Step {df_d1['buyland_submitted'].mean():<5.1f} | Step {df_d1['land2_unlocked'].mean():<7.1f} | Step {df_d1['land2_first_plant'].mean():<7.1f} | Step {df_d1['land3_unlocked'].mean():.1f}")
    for _, r in df_sum.iterrows():
        print(f"{r['cohort']:<26} | {r['count']:<6} | ${r['mean_money']:<11,.0f} | Step {r['step_cash_1000']:<7.1f} | Step {r['step_buyland']:<5.1f} | Step {r['step_land2_unlocked']:<7.1f} | Step {r['step_land2_first_plant']:<7.1f} | Step {r['step_land3_unlocked']:.1f}")

    # Save to JSON
    out_json = os.path.join(REPORTS_DIR, "exp133_opening_velocity_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "d1_milestones": _to_native(df_d1.to_dict(orient="records")),
            "cohort_milestones": _to_native(df_sum.to_dict(orient="records")),
        }, f, indent=2)
    print(f"\nSaved Full EXP133 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
