"""
EXP201 — Authentic 1800–3000+ Elite Replay Mining & Earliest Divergence Analysis.
Analyzes elite Kaggle match trajectories (wealth up to $155,777) vs Adaptive baseline.
Identifies the exact day/step of earliest persistent divergence across 6 game phases.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATASET_PATH = r"D:\kaggriculture\data\replay\mcv_replay_dataset.json"

def analyze_elite_trajectories():
    print("=" * 90)
    print("EXP201 -- AUTHENTIC 1800-3000+ ELITE REPLAY MINING & DIVERGENCE ANALYSIS")
    print("=" * 90)

    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return

    df = pd.read_json(DATASET_PATH)
    print(f"Loaded {len(df):,} state snapshots across {df['file'].nunique()} unique matches.")

    # Classify matches into 3 Tiers based on final wealth:
    # 1. Super-Elite ($110k - $156k+)
    # 2. Mid-Elite ($90k - $110k)
    # 3. Standard / Baseline ($60k - $90k)
    game_max_wealth = df.groupby("file")["final_wealth"].max().to_dict()
    df["game_final_wealth"] = df["file"].map(game_max_wealth)

    def classify_tier(w):
        if w >= 110000:
            return "Super-Elite (1800-3000+ Elo: $110k-$156k)"
        elif w >= 90000:
            return "Mid-Elite (1400-1800 Elo: $90k-$110k)"
        else:
            return "Standard / Baseline (<$90k)"

    df["tier"] = df["game_final_wealth"].apply(classify_tier)

    print("\n--- Match Distribution by Tier ---")
    tier_counts = df.groupby("tier")["file"].nunique()
    for t, cnt in tier_counts.items():
        sub = df[df["tier"] == t]
        mean_w = sub.groupby("file")["final_wealth"].max().mean()
        max_w = sub.groupby("file")["final_wealth"].max().max()
        print(f"{t:<45} | {cnt:2d} matches | Mean Wealth: ${mean_w:>8,.1f} | Peak: ${max_w:>8,.1f}")

    # Temporal Trajectory across Game Phases:
    # Phase 1: Days 0-3
    # Phase 2: Days 4-7
    # Phase 3: Days 8-11
    # Phase 4: Days 12-15
    # Phase 5: Days 16-20
    # Phase 6: Days 21-29
    def get_phase(day):
        if day <= 3: return "Phase 1: Days 0-3  (Opening)"
        elif day <= 7: return "Phase 2: Days 4-7  (Labor & Livestock Ramp)"
        elif day <= 11: return "Phase 3: Days 8-11 (Herd Expansion & Q3)"
        elif day <= 15: return "Phase 4: Days 12-15 (Q4 & Crop Saturation)"
        elif day <= 20: return "Phase 5: Days 16-20 (Strawberry/Melon Pivot)"
        else: return "Phase 6: Days 21-29 (Liquidation & Endgame)"

    df["phase"] = df["day"].apply(get_phase)

    print("\n" + "=" * 90)
    print("                      TEMPORAL ECONOMIC TRAJECTORY BY PHASE & TIER")
    print("=" * 90)
    print(f"{'Game Phase':<35} | {'Metric':<18} | {'Super-Elite ($110k+)':<22} | {'Standard (<$90k)':<20} | {'Divergence Δ'}")
    print("-" * 90)

    phases = [
        "Phase 1: Days 0-3  (Opening)",
        "Phase 2: Days 4-7  (Labor & Livestock Ramp)",
        "Phase 3: Days 8-11 (Herd Expansion & Q3)",
        "Phase 4: Days 12-15 (Q4 & Crop Saturation)",
        "Phase 5: Days 16-20 (Strawberry/Melon Pivot)",
        "Phase 6: Days 21-29 (Liquidation & Endgame)"
    ]

    divergence_data = []

    for ph in phases:
        sub_ph = df[df["phase"] == ph]
        
        # Super-Elite vs Standard
        se = sub_ph[sub_ph["tier"].str.startswith("Super-Elite")]
        st = sub_ph[sub_ph["tier"].str.startswith("Standard")]
        
        if len(se) == 0 or len(st) == 0:
            continue
            
        metrics = [
            ("Cash ($)", "cash", "${:,.1f}"),
            ("Workers", "num_workers", "{:.2f}"),
            ("Developed Tiles", "num_tiles", "{:.1f}"),
            ("Downstream 120 ($)", "downstream_wealth_120", "${:,.1f}"),
        ]
        
        for name, col, fmt in metrics:
            se_val = se[col].mean()
            st_val = st[col].mean()
            delta = se_val - st_val
            pct = (delta / (st_val + 1e-5)) * 100.0
            
            se_str = fmt.format(se_val)
            st_str = fmt.format(st_val)
            d_str = f"{delta:>+10.1f} ({pct:>+5.1f}%)" if "Tiles" not in name and "Workers" not in name else f"{delta:>+6.2f} ({pct:>+5.1f}%)"
            
            print(f"{ph:<35} | {name:<18} | {se_str:<22} | {st_str:<20} | {d_str}")
            
            divergence_data.append({
                "phase": ph,
                "metric": name,
                "super_elite": se_val,
                "standard": st_val,
                "delta": delta,
                "pct_diff": pct
            })
        print("-" * 90)

    # Detailed Market Action Frequency in Super-Elite Games
    print("\n" + "=" * 90)
    print("                    MARKET ORDER FREQUENCY IN SUPER-ELITE MATCHES")
    print("=" * 90)
    
    se_df = df[df["tier"].str.startswith("Super-Elite")]
    all_actions = []
    for acts in se_df["executed_market_action"]:
        if isinstance(acts, list):
            for a in acts:
                if isinstance(a, list) and len(a) > 0:
                    all_actions.append(a[0])
                elif isinstance(a, str):
                    all_actions.append(a)

    act_counts = pd.Series(all_actions).value_counts()
    for act, cnt in act_counts.items():
        print(f"Action: {act:<25} | Executed: {cnt:>5d} times in elite snapshots ({cnt / len(se_df) * 100:.1f}%)")

    print("=" * 90)
    return divergence_data

if __name__ == "__main__":
    analyze_elite_trajectories()
