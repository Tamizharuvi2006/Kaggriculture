"""EXP138: Detailed 720-Step Trajectory Analysis of Real Kaggle Losses against >1200 Opponents."""
from __future__ import annotations
import os
import sys
import glob
import json
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

def main():
    raw_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "**", "episode-*-replay.json"), recursive=True)
    ppo_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "**", "episode-*-replay.json"), recursive=True)
    all_replays = raw_replays + ppo_replays

    print(f"Analyzing {len(all_replays)} full 720-step replays against real Kaggle tournament opponents...")

    trajectory_records = []

    for r_path in all_replays:
        try:
            with open(r_path, "r", encoding="utf-8") as f:
                rep = json.load(f)
            steps = rep.get("steps", [])
            if len(steps) < 720:
                continue

            r0 = float(steps[-1][0].get("reward") or 0.0)
            r1 = float(steps[-1][1].get("reward") or 0.0)
            ep_id = os.path.basename(r_path).replace("-replay.json", "").replace("episode-", "")

            # Track checkpoints
            rec = {
                "ep_id": ep_id,
                "reward_hero": r0,
                "reward_opp": r1,
                "won": (r0 > r1),
                "margin": (r0 - r1),
            }

            for day in [5, 10, 15, 20, 24, 28, 30]:
                s_idx = min(719, (day * 24) - 1)
                st = steps[s_idx]
                obs0 = st[0].get("observation", {}) or {}
                farms = obs0.get("farms", [{}, {}])
                f0 = farms[0] if len(farms) > 0 else {}
                f1 = farms[1] if len(farms) > 1 else {}
                mkt = obs0.get("market", {}) or {}
                prices = mkt.get("prices", mkt.get("current_prices", {})) or {}

                # Hero state
                rec[f"d{day}_c0"] = float(f0.get("money") or 0.0)
                # Opponent state
                rec[f"d{day}_c1"] = float(f1.get("money") or 0.0)
                # Market prices
                rec[f"d{day}_p_straw"] = float(prices.get("STRAWBERRY") or 120.0)
                rec[f"d{day}_p_milk"] = float(prices.get("MILK") or 100.0)
                rec[f"d{day}_p_wool"] = float(prices.get("WOOL") or 180.0)
                rec[f"d{day}_p_wheat"] = float(prices.get("WHEAT") or 35.0)

                # Opponent livestock & crops
                tiles1 = f1.get("tiles", []) or []
                cows1 = sum(1 for row in tiles1 for t in row if isinstance(t, dict) and t.get("animal") == "COW")
                sheep1 = sum(1 for row in tiles1 for t in row if isinstance(t, dict) and t.get("animal") == "SHEEP")
                straws1 = sum(1 for row in tiles1 for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                melons1 = sum(1 for row in tiles1 for t in row if isinstance(t, dict) and t.get("crop") == "MELON")

                rec[f"d{day}_opp_cows"] = cows1
                rec[f"d{day}_opp_sheep"] = sheep1
                rec[f"d{day}_opp_straws"] = straws1
                rec[f"d{day}_opp_melons"] = melons1

            trajectory_records.append(rec)
        except Exception as e:
            pass

    df = pd.DataFrame(trajectory_records)
    print(f"\nSuccessfully parsed {len(df)} 720-step tournament matches ({df['won'].sum()} wins, {(~df['won']).sum()} losses).")

    print("\n" + "=" * 135)
    print(f"STEP-BY-STEP CHECKPOINT PROGRESSION IN LOSS MATCHES (MEAN VALUES):")
    print("=" * 135)
    print(f"{'Game Day':<10} | {'Hero Cash':<12} | {'Opp Cash':<12} | {'Cash Margin':<12} | {'Straw Price':<12} | {'Milk Price':<12} | {'Opp Cows':<10} | {'Opp Sheep':<10} | {'Opp Straws':<10}")
    print("-" * 135)

    losses_df = df[~df["won"]]
    for day in [5, 10, 15, 20, 24, 28, 30]:
        c0 = losses_df[f"d{day}_c0"].mean()
        c1 = losses_df[f"d{day}_c1"].mean()
        margin = c0 - c1
        p_straw = losses_df[f"d{day}_p_straw"].mean()
        p_milk = losses_df[f"d{day}_p_milk"].mean()
        opp_c = losses_df[f"d{day}_opp_cows"].mean()
        opp_s = losses_df[f"d{day}_opp_sheep"].mean()
        opp_st = losses_df[f"d{day}_opp_straws"].mean()

        print(f"Day {day:02d}     | ${c0:10,.0f} | ${c1:10,.0f} | ${margin:+10,.0f} | ${p_straw:10.1f} | ${p_milk:10.1f} | {opp_c:8.1f}   | {opp_s:8.1f}   | {opp_st:8.1f}")

    print("=" * 135)

if __name__ == "__main__":
    main()
