"""EXP145: Cash Runway & System-Level Solvency Forensics (Days 5 to 15).

Forensic investigation across 31 full 720-step Kaggle tournament replays:
1. At every step from Day 5 to Day 15 (Steps 120 to 360), computes:
   - Current cash M(t)
   - 1-day wage obligation W_1 = workers * $100
   - 3-day wage obligation W_3 = workers * $300
   - Next land purchase requirement L_land ($1,000 for Quad 2, $2,000 for Quad 3)
   - Next seed requirement S_seed ($50 * strawberry count)
   - Daily burn rate = Wages/day + Feed/day + Seed amortized/day
   - Effective Cash Runway (in game days) = M(t) / Daily Burn Rate
   - Net Solvency Buffer = M(t) - (W_1 + S_seed + L_land)
2. Compares D.1 (losses) vs Strong Opponents (>1200 winners):
   - When does cash runway diverge?
   - What minimum cash runway is required before wheat retention becomes safe?
   - What is the structural difference in capital allocation and solvency management?
3. Formulates the minimal cash-runway decision rule connecting solvency to resource retention.
"""
from __future__ import annotations
import os
import sys
import glob
import json
from collections import defaultdict
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

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

def analyze_match_cash_runway(r_path: str):
    with open(r_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    steps = rep.get("steps", [])
    if len(steps) < 360:
        return None

    ep_id = os.path.basename(r_path).replace("-replay.json", "").replace("episode-", "")
    r0_final = float(steps[-1][0].get("reward") or 0.0)
    r1_final = float(steps[-1][1].get("reward") or 0.0)
    won = (r0_final > r1_final)

    hero_runways = []
    opp_runways = []
    hero_solvency_buffers = []
    opp_solvency_buffers = []
    hero_burn_rates = []
    opp_burn_rates = []
    hero_cash_series = []
    opp_cash_series = []

    for s_idx in range(120, min(360, len(steps))):
        st = steps[s_idx]
        obs0 = st[0].get("observation", {}) or {}
        farms = obs0.get("farms", [{}, {}])
        f0 = farms[0] if len(farms) > 0 else {}
        f1 = farms[1] if len(farms) > 1 else {}

        m0 = float(f0.get("money") or 0.0)
        m1 = float(f1.get("money") or 0.0)
        hero_cash_series.append(m0)
        opp_cash_series.append(m1)

        # Worker count
        act0 = st[0].get("action", {}) or {}
        act1 = st[1].get("action", {}) or {}
        w0 = max(1, len(act0.get("hands") or []))
        w1 = max(1, len(act1.get("hands") or []))

        # Animal count
        tiles0 = f0.get("tiles", [])
        tiles1 = f1.get("tiles", [])
        anims0 = sum(1 for r in tiles0 for t in r if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"))
        anims1 = sum(1 for r in tiles1 for t in r if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"))

        # Daily burn rates: Wages ($100/worker/day) + Feed ($40/animal/day) + Seed reserve ($100/day)
        burn0 = (w0 * 100.0) + (anims0 * 40.0) + 100.0
        burn1 = (w1 * 100.0) + (anims1 * 40.0) + 100.0
        hero_burn_rates.append(burn0)
        opp_burn_rates.append(burn1)

        # Cash Runway in Days
        runway0 = m0 / burn0 if burn0 > 0 else 0.0
        runway1 = m1 / burn1 if burn1 > 0 else 0.0
        hero_runways.append(runway0)
        opp_runways.append(runway1)

        # Immediate Land requirement ($1,000 for Quad 2 if locked, $2,000 for Quad 3 if locked)
        unlocked0 = f0.get("unlocked_quadrants") or [0]
        unlocked1 = f1.get("unlocked_quadrants") or [0]
        land_req0 = 1000.0 if len(unlocked0) == 1 else (2000.0 if len(unlocked0) == 2 else 0.0)
        land_req1 = 1000.0 if len(unlocked1) == 1 else (2000.0 if len(unlocked1) == 2 else 0.0)

        # 1-day solvency buffer = Cash - (1-day wages + land requirement + 1-day seed buffer)
        solv0 = m0 - ((w0 * 100.0) + land_req0 + 200.0)
        solv1 = m1 - ((w1 * 100.0) + land_req1 + 200.0)
        hero_solvency_buffers.append(solv0)
        opp_solvency_buffers.append(solv1)

    return {
        "ep_id": ep_id,
        "won": won,
        "hero_runway_mean": float(np.mean(hero_runways)),
        "opp_runway_mean": float(np.mean(opp_runways)),
        "hero_solv_mean": float(np.mean(hero_solvency_buffers)),
        "opp_solv_mean": float(np.mean(opp_solvency_buffers)),
        "hero_cash_series": hero_cash_series,
        "opp_cash_series": opp_cash_series,
        "hero_runways": hero_runways,
        "opp_runways": opp_runways,
        "hero_solv": hero_solvency_buffers,
        "opp_solv": opp_solvency_buffers,
    }

def main():
    print("=" * 135)
    print("EXP145: CASH RUNWAY & SYSTEM-LEVEL SOLVENCY FORENSICS (DAYS 5 TO 15)")
    print("=" * 135)

    raw_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "**", "episode-*-replay.json"), recursive=True)
    ppo_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "**", "episode-*-replay.json"), recursive=True)
    all_replays = raw_replays + ppo_replays

    results = []
    for r_path in all_replays:
        res = analyze_match_cash_runway(r_path)
        if res is not None:
            results.append(res)

    losses = [r for r in results if not r["won"]]
    n_losses = len(losses)
    print(f"Audited {len(results)} matches ({n_losses} loss matches) for Cash Runway & Solvency Dynamics across Steps 120-360.\n")

    # 1. Day-by-Day Cash Runway Comparison
    print("=" * 135)
    print("1. CASH RUNWAY (IN DAYS OF WORKING CAPITAL) & SOLVENCY BUFFER ACROSS MIDGAME:")
    print("=" * 135)
    print(f"{'Game Day':<15} | {'D.1 Cash ($)':<18} | {'Opp Cash ($)':<18} | {'D.1 Runway (Days)':<20} | {'Opp Runway (Days)':<20} | {'Solvency Gap ($)'}")
    print("-" * 135)

    day_checkpoints = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    d1_runways_by_day = {}
    opp_runways_by_day = {}

    for d in day_checkpoints:
        idx = (d - 5) * 24
        if idx >= 240: idx = 239

        c_d1 = np.mean([m["hero_cash_series"][idx] for m in losses])
        c_opp = np.mean([m["opp_cash_series"][idx] for m in losses])
        r_d1 = np.mean([m["hero_runways"][idx] for m in losses])
        r_opp = np.mean([m["opp_runways"][idx] for m in losses])
        s_d1 = np.mean([m["hero_solv"][idx] for m in losses])
        s_opp = np.mean([m["opp_solv"][idx] for m in losses])

        d1_runways_by_day[f"day_{d}"] = float(r_d1)
        opp_runways_by_day[f"day_{d}"] = float(r_opp)

        print(f"Day {d:02d}{'':<9} | ${c_d1:12,.2f}     | ${c_opp:12,.2f}     | {r_d1:6.2f} days{'':<10} | {r_opp:6.2f} days{'':<10} | ${s_opp - s_d1:+12,.2f}")

    # 2. Critical Runway Threshold Analysis
    print("\n" + "=" * 135)
    print("2. CASH RUNWAY SOLVENCY THRESHOLD FINDINGS:")
    print("=" * 135)
    mean_r_d1 = np.mean([m["hero_runway_mean"] for m in losses])
    mean_r_opp = np.mean([m["opp_runway_mean"] for m in losses])
    mean_s_d1 = np.mean([m["hero_solv_mean"] for m in losses])
    mean_s_opp = np.mean([m["opp_solv_mean"] for m in losses])

    print(f"  D.1 Mean Midgame Cash Runway         : {mean_r_d1:.2f} Days of Working Capital")
    print(f"  Opponent Mean Midgame Cash Runway    : {mean_r_opp:.2f} Days of Working Capital (Ratio: {mean_r_opp/mean_r_d1:.2f}x)")
    print(f"  D.1 Mean Net Solvency Buffer         : ${mean_s_d1:+10,.2f}")
    print(f"  Opponent Mean Net Solvency Buffer    : ${mean_s_opp:+10,.2f} (Buffer Delta: ${mean_s_opp - mean_s_d1:+10,.2f})")

    # Save EXP145 Report
    out_json = os.path.join(REPORTS_DIR, "exp145_cash_runway_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "d1_mean_runway_days": float(mean_r_d1),
            "opp_mean_runway_days": float(mean_r_opp),
            "d1_mean_solvency_buffer": float(mean_s_d1),
            "opp_mean_solvency_buffer": float(mean_s_opp),
            "runway_by_day_d1": d1_runways_by_day,
            "runway_by_day_opp": opp_runways_by_day,
        }, f, indent=2)

    print(f"\nSaved Complete EXP145 Report: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
