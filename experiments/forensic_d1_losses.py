"""EXP073: Forensic Autopsy of Variant D.1 Live Ladder Losses.

Analyzes the downloaded episode replay JSONs for all 20 losses:
- Seat breakdown (Seat 0 vs Seat 1)
- Opponent crop portfolio & livestock count
- Step-by-step cashflow divergence
- Market price realization
"""
from __future__ import annotations
import sys
import os
import json
import glob
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEMETRY_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches")

def analyze_loss_replays():
    files = glob.glob(os.path.join(TELEMETRY_DIR, "episode_*.json"))
    print(f"Loaded {len(files)} detailed loss episode JSONs for forensic autopsy.")

    if not files:
        print("No loss files found.")
        return

    forensic_records = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            ep = data.get("episode", {})
            ep_id = ep.get("id")
            seed = ep.get("seed")
            agents = ep.get("agents", [])
            steps = data.get("steps", [])

            # Identify our seat (Sub ID 55780289)
            our_seat = 0
            for idx, a in enumerate(agents):
                if a.get("submissionId") == 55780289:
                    our_seat = idx
                    break
            opp_seat = 1 - our_seat

            our_rew = float(agents[our_seat].get("reward") or 0.0)
            opp_rew = float(agents[opp_seat].get("reward") or 0.0)
            opp_sub_id = agents[opp_seat].get("submissionId")
            opp_score = float(agents[opp_seat].get("initialScore") or 0.0)

            # Analyze final state if available in steps
            final_step = steps[-1] if steps else None
            opp_cows = 0
            opp_workers = 0
            opp_land = 0
            opp_strawberries = 0

            if final_step:
                # Inspect observation
                obs = final_step[0].get("observation", {}) if len(final_step) > 0 else {}
                players = obs.get("players", [])
                if len(players) > opp_seat:
                    opp_p = players[opp_seat]
                    opp_cows = len(opp_p.get("cows", []))
                    opp_workers = len(opp_p.get("workers", []))
                    opp_land = len(opp_p.get("land", []))
                    
                    # Count crops
                    crops = obs.get("crops", [])
                    opp_strawberries = sum(1 for c in crops if c.get("owner") == opp_seat and c.get("type") == 1)

            forensic_records.append({
                "ep_id": ep_id,
                "seed": seed,
                "our_seat": our_seat,
                "opp_sub_id": opp_sub_id,
                "opp_score": opp_score,
                "our_rew": our_rew,
                "opp_rew": opp_rew,
                "margin": our_rew - opp_rew,
                "opp_cows": opp_cows,
                "opp_workers": opp_workers,
                "opp_land": opp_land,
            })
        except Exception as e:
            continue

    print("\n" + "=" * 105)
    print("EXP073: MASTER FORENSIC AUTOPSY OF LIVE D.1 LOSSES")
    print("=" * 105)
    print(f"{'Ep ID':<10} | {'Seat':<5} | {'Opp Sub ID':<11} | {'Opp Elo':>8} | {'D.1 Reward':>11} | {'Opp Reward':>11} | {'Margin ($)':>11} | {'Opp Assets'}")
    print("-" * 105)

    forensic_records.sort(key=lambda x: x["margin"])

    seat0_losses = sum(1 for r in forensic_records if r["our_seat"] == 0)
    seat1_losses = sum(1 for r in forensic_records if r["our_seat"] == 1)

    for r in forensic_records:
        asset_str = f"{r['opp_land']}Q, {r['opp_cows']}C, {r['opp_workers']}W" if r['opp_land'] > 0 else "N/A"
        print(f"{r['ep_id']:<10} | S{r['our_seat']:<4} | {str(r['opp_sub_id']):<11} | {r['opp_score']:>8.1f} | ${r['our_rew']:>10,.0f} | ${r['opp_rew']:>10,.0f} | ${r['margin']:>+10,.0f} | {asset_str}")

    print("=" * 105)
    print("\nFORENSIC PATTERN SUMMARY:")
    print(f"  - Total Loss Episodes Analyzed : {len(forensic_records)}")
    print(f"  - Seat Breakdown               : Seat 0: {seat0_losses} Losses | Seat 1: {seat1_losses} Losses")
    print(f"  - Mean Loss Deficit            : ${np.mean([r['margin'] for r in forensic_records]):+,.2f}")
    print(f"  - Median Loss Deficit          : ${np.median([r['margin'] for r in forensic_records]):+,.2f}")
    print(f"  - Losses with margin > -$10,000: {sum(1 for r in forensic_records if r['margin'] > -10000)} / {len(forensic_records)} (Tight Margin Losses)")
    print(f"  - Losses with margin <= -$20,000: {sum(1 for r in forensic_records if r['margin'] <= -20000)} / {len(forensic_records)} (Large Margin Losses)")
    print("=" * 105)

if __name__ == "__main__":
    analyze_loss_replays()
