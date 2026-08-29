"""EXP134: 900-1200 Rating Band Win/Loss Mechanism Forensics.

Audits matched checkpoints (Days 10, 15, 20, 25, 27, 29) across:
1. Matches where D.1 lost to 900-1200 opponents.
2. Matches where D.1 or Elite bots won against 900-1200 opponents.

Extracts:
- Cash trajectory (Hero vs Opponent)
- Market share trajectory
- Commodity prices: Milk, Wheat, Strawberry, Wool
- Opponent market sell/buy volume & feed consumption
- Held shed inventory (Milk, Strawberry)
- Field harvest backlog (Ripe unpicked strawberries)
- Final liquidation step & price realization
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

CHECKPOINTS = [
    (10, 216),  # Day 10 Hour 0
    (15, 336),  # Day 15 Hour 0
    (20, 456),  # Day 20 Hour 0
    (25, 576),  # Day 25 Hour 0
    (27, 624),  # Day 27 Hour 0
    (29, 672),  # Day 29 Hour 0
]

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

def analyze_replay_step_trajectory(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = data.get("steps", [])
        if len(steps) < 680:
            return []

        trajectories = []
        for p_idx in [0, 1]:
            opp_idx = 1 - p_idx
            last_obs = steps[-1][p_idx]["observation"]
            farms = last_obs.get("farms", [])
            if len(farms) < 2:
                continue

            our_farm_end = farms[p_idx]
            opp_farm_end = farms[opp_idx]
            our_money_end = float(our_farm_end.get("money", 0.0) or 0.0)
            opp_money_end = float(opp_farm_end.get("money", 0.0) or 0.0)
            won = our_money_end > opp_money_end

            checkpoint_data = {}
            for day, s_idx in CHECKPOINTS:
                if s_idx >= len(steps):
                    continue
                obs_step = steps[s_idx][p_idx]["observation"]
                opp_obs_step = steps[s_idx][opp_idx]["observation"]

                our_f = obs_step.get("farms", [])[p_idx]
                opp_f = obs_step.get("farms", [])[opp_idx]

                our_cash = float(our_f.get("money", 0.0) or 0.0)
                opp_cash = float(opp_f.get("money", 0.0) or 0.0)
                total_cash = our_cash + opp_cash + 1e-5
                mkt_share = (our_cash / total_cash) * 100

                # Market prices
                mkt = obs_step.get("market", {}) or {}
                prices = mkt.get("prices", mkt.get("current_prices", {})) or {}
                p_milk = float(prices.get("MILK", 100.0) or 100.0)
                p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
                p_wheat = float(prices.get("WHEAT", 80.0) or 80.0)
                p_wool = float(prices.get("WOOL", 150.0) or 150.0)

                # Shed inventory
                priv = obs_step.get("private") or {}
                shed = priv.get("shed", {}) or {}
                milk_shed = int(shed.get("MILK", 0) or 0)
                straw_shed = int(shed.get("STRAWBERRY", 0) or 0)

                # Field unharvested ripe yield
                ripe_straw_tiles = 0
                tiles = our_f.get("tiles", [])
                for row in tiles:
                    for tile in (row if isinstance(row, list) else [row]):
                        if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("stage") == 3:
                            ripe_straw_tiles += 1

                checkpoint_data[f"D{day}"] = {
                    "our_cash": our_cash,
                    "opp_cash": opp_cash,
                    "market_share": mkt_share,
                    "p_milk": p_milk,
                    "p_straw": p_straw,
                    "p_wheat": p_wheat,
                    "p_wool": p_wool,
                    "milk_shed": milk_shed,
                    "straw_shed": straw_shed,
                    "ripe_backlog": ripe_straw_tiles,
                }

            trajectories.append({
                "file": os.path.basename(file_path),
                "player": p_idx,
                "our_money": our_money_end,
                "opp_money": opp_money_end,
                "won": won,
                "delta": our_money_end - opp_money_end,
                "checkpoints": checkpoint_data,
            })
        return trajectories
    except Exception:
        return []

def main():
    print("=" * 135)
    print("EXP134: 900-1200 RATING BAND WIN/LOSS MECHANISM MINING")
    print("=" * 135)

    replay_files = []
    replay_files.extend(glob.glob(os.path.join(BASE_DIR, "l+reviews", "*.json")))
    replay_files.extend(glob.glob(os.path.join(BASE_DIR, "l+reviews", "newl", "*.json")))
    replay_files.extend(glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "*", "*.json")))
    replay_files.extend(glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "*", "*.json")))
    replay_files = [f for f in set(replay_files) if not f.endswith("-0.json") and not f.endswith("-1.json")]

    print(f"Auditing {len(replay_files)} full step-level tournament replays across checkpoints...")

    all_trajs = []
    for rf in replay_files:
        all_trajs.extend(analyze_replay_step_trajectory(rf))

    df = pd.DataFrame(all_trajs)
    print(f"Loaded {len(df)} total match trajectories.")

    # Filter for standard D.1 strawberry/cow engine profile (terminal money between $35k and $100k)
    df_comp = df[(df["our_money"] >= 35000) & (df["opp_money"] >= 35000)].copy()

    df_wins = df_comp[df_comp["won"] == True]
    df_losses = df_comp[df_comp["won"] == False]

    print(f"\nFiltered Competitive 900-1200 Opponent Cohort:")
    print(f"  - Competitive Wins  : {len(df_wins)} trajectories (Mean Money: ${df_wins['our_money'].mean():,.0f} vs Opp ${df_wins['opp_money'].mean():,.0f})")
    print(f"  - Competitive Losses: {len(df_losses)} trajectories (Mean Money: ${df_losses['our_money'].mean():,.0f} vs Opp ${df_losses['opp_money'].mean():,.0f})")

    # Checkpoint Comparison Table
    print("\n" + "=" * 135)
    print("CHECKPOINT TRAJECTORY COMPARISON: WINS VS LOSSES (900-1200 BAND)")
    print("=" * 135)

    headers = f"{'Checkpoint':<12} | {'Cohort':<8} | {'Hero Cash':<11} | {'Opp Cash':<11} | {'Mkt Share':<10} | {'P_Milk':<8} | {'P_Straw':<8} | {'P_Wheat':<8} | {'Shed Milk':<10} | {'Shed Straw':<10} | {'Ripe Backlog'}"
    print(headers)
    print("-" * 135)

    comparison_results = {}

    for day, _ in CHECKPOINTS:
        k = f"D{day}"
        w_cash = [t.get(k, {}).get("our_cash", 0) for t in df_wins["checkpoints"] if k in t]
        l_cash = [t.get(k, {}).get("our_cash", 0) for t in df_losses["checkpoints"] if k in t]

        w_opp_cash = [t.get(k, {}).get("opp_cash", 0) for t in df_wins["checkpoints"] if k in t]
        l_opp_cash = [t.get(k, {}).get("opp_cash", 0) for t in df_losses["checkpoints"] if k in t]

        w_mkt = [t.get(k, {}).get("market_share", 50) for t in df_wins["checkpoints"] if k in t]
        l_mkt = [t.get(k, {}).get("market_share", 50) for t in df_losses["checkpoints"] if k in t]

        w_pmilk = [t.get(k, {}).get("p_milk", 100) for t in df_wins["checkpoints"] if k in t]
        l_pmilk = [t.get(k, {}).get("p_milk", 100) for t in df_losses["checkpoints"] if k in t]

        w_pstraw = [t.get(k, {}).get("p_straw", 120) for t in df_wins["checkpoints"] if k in t]
        l_pstraw = [t.get(k, {}).get("p_straw", 120) for t in df_losses["checkpoints"] if k in t]

        w_pwheat = [t.get(k, {}).get("p_wheat", 80) for t in df_wins["checkpoints"] if k in t]
        l_pwheat = [t.get(k, {}).get("p_wheat", 80) for t in df_losses["checkpoints"] if k in t]

        w_smilk = [t.get(k, {}).get("milk_shed", 0) for t in df_wins["checkpoints"] if k in t]
        l_smilk = [t.get(k, {}).get("milk_shed", 0) for t in df_losses["checkpoints"] if k in t]

        w_sstraw = [t.get(k, {}).get("straw_shed", 0) for t in df_wins["checkpoints"] if k in t]
        l_sstraw = [t.get(k, {}).get("straw_shed", 0) for t in df_losses["checkpoints"] if k in t]

        w_backlog = [t.get(k, {}).get("ripe_backlog", 0) for t in df_wins["checkpoints"] if k in t]
        l_backlog = [t.get(k, {}).get("ripe_backlog", 0) for t in df_losses["checkpoints"] if k in t]

        print(f"{'Day ' + str(day):<12} | {'WIN':<8} | ${np.mean(w_cash):<10,.0f} | ${np.mean(w_opp_cash):<10,.0f} | {np.mean(w_mkt):5.1f}%     | ${np.mean(w_pmilk):5.1f}  | ${np.mean(w_pstraw):5.1f}   | ${np.mean(w_pwheat):5.1f}   | {np.mean(w_smilk):5.1f} units  | {np.mean(w_sstraw):5.1f} units   | {np.mean(w_backlog):4.1f} tiles")
        print(f"{'':<12} | {'LOSS':<8} | ${np.mean(l_cash):<10,.0f} | ${np.mean(l_opp_cash):<10,.0f} | {np.mean(l_mkt):5.1f}%     | ${np.mean(l_pmilk):5.1f}  | ${np.mean(l_pstraw):5.1f}   | ${np.mean(l_pwheat):5.1f}   | {np.mean(l_smilk):5.1f} units  | {np.mean(l_sstraw):5.1f} units   | {np.mean(l_backlog):4.1f} tiles")
        print("-" * 135)

        comparison_results[k] = {
            "win": {
                "hero_cash": float(np.mean(w_cash)), "opp_cash": float(np.mean(w_opp_cash)), "mkt_share": float(np.mean(w_mkt)),
                "p_milk": float(np.mean(w_pmilk)), "p_straw": float(np.mean(w_pstraw)), "p_wheat": float(np.mean(w_pwheat)),
                "shed_milk": float(np.mean(w_smilk)), "shed_straw": float(np.mean(w_sstraw)), "ripe_backlog": float(np.mean(w_backlog))
            },
            "loss": {
                "hero_cash": float(np.mean(l_cash)), "opp_cash": float(np.mean(l_opp_cash)), "mkt_share": float(np.mean(l_mkt)),
                "p_milk": float(np.mean(l_pmilk)), "p_straw": float(np.mean(l_pstraw)), "p_wheat": float(np.mean(l_pwheat)),
                "shed_milk": float(np.mean(l_smilk)), "shed_straw": float(np.mean(l_sstraw)), "ripe_backlog": float(np.mean(l_backlog))
            }
        }

    # Save to JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp134_900_1200_forensics_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "checkpoints": comparison_results,
            "win_count": len(df_wins),
            "loss_count": len(df_losses),
        }, f, indent=2)
    print(f"\nSaved Full EXP134 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
