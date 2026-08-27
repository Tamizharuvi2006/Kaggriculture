"""EXP117: Post-Day 10 Elite Macro Separation & Behavioral Forensics.

Mines the 8,268 Kaggle Replay Corpus to uncover the exact micro/macro divergence that separates
the 3000+ elite winners (Clusters 87, 59, 84, 99, 73, 76) from the 50/50 D.1 baseline after Day 10:

Key Questions Investigated:
1. Quadrant Expansion: Do elite winners stay capped at 3 Quadrants (NW+NE+SW) or unlock Quadrant 4 (SE)?
2. Worker Saturation: Does the worker headcount peak at 13 hands, or ramp to 14-16 hands?
3. Livestock Scaling: Do elite agents cap at 8 cows, or scale to 12+ cows / dual cow+sheep herds?
4. Arable Capacity & Secondary Crops: How do elite agents monetize idle arable tiles during Days 11-25?
5. Terminal Reinvestment Cutoff: At what exact day/hour do elite winners stop reinvesting capital into inputs?
6. Market Timing & Liquidation Frequency: What is their exact sales cadence under price fluctuations?
"""
from __future__ import annotations
import os
import sys
import json
import gzip
import pandas as pd
import numpy as np
from collections import defaultdict
from huggingface_hub import hf_hub_download

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATASETS_IL = os.path.join(BASE_DIR, "datasets", "il")
EPISODES_DIR = os.path.join(DATASETS_IL, "episodes")
os.makedirs(EPISODES_DIR, exist_ok=True)

# Load HF Token
hf_token_path = os.path.expanduser("~/.hf/HF_TOKEN")
HF_TOKEN = None
if os.path.exists(hf_token_path):
    with open(hf_token_path, "r", encoding="utf-8") as f:
        HF_TOKEN = f.read().strip()
    os.environ["HF_TOKEN"] = HF_TOKEN

def get_episode_path(episode_id: int) -> str | None:
    local_path = os.path.join(EPISODES_DIR, f"{episode_id}.json.gz")
    if os.path.exists(local_path):
        return local_path
    rel_hf_path = f"datasets/il/episodes/{episode_id}.json.gz"
    try:
        downloaded = hf_hub_download(
            repo_id="KiroSamurai/kaggriculture-il",
            filename=rel_hf_path,
            repo_type="dataset",
            local_dir=BASE_DIR,
            token=HF_TOKEN,
        )
        return downloaded
    except Exception as e:
        return None

def analyze_episode_post_day10(episode_path: str, seat: int):
    with gzip.open(episode_path, "rt", encoding="utf-8") as f:
        data = json.load(f)

    steps = data.get("steps", [])
    if not steps:
        return None

    timeline = {
        "lands_by_day": {},
        "workers_by_day": {},
        "cows_by_day": {},
        "sheep_by_day": {},
        "strawberries_by_day": {},
        "other_crops_by_day": {},
        "cash_by_day": {},
        "last_buy_seed_step": 0,
        "last_buy_animal_step": 0,
        "last_hire_step": 0,
        "total_quadrants": 1,
        "total_workers": 1,
        "total_cows": 0,
        "total_sheep": 0,
        "terminal_bank": 0.0,
        "sales_by_commodity": defaultdict(float),
        "sales_cadence_days_10_25": 0,
    }

    for step_idx, step_data in enumerate(steps):
        if not isinstance(step_data, list) or len(step_data) <= seat:
            continue
        state = step_data[seat]
        obs = state.get("observation", {})
        farms = obs.get("farms", [])
        if len(farms) <= seat:
            continue

        farm = farms[seat]
        day = (step_idx // 24) + 1
        money = float(farm.get("money", 0.0))
        hands = len(farm.get("hands", []))
        quadrants = len(farm.get("unlocked_quadrants", []))

        # Count live tiles
        cow_count = 0
        sheep_count = 0
        straw_count = 0
        other_crop_count = 0

        for row in farm.get("tiles", []) or []:
            for tile in row if isinstance(row, list) else [row]:
                if not isinstance(tile, dict): continue
                a = str(tile.get("animal", "")).upper()
                c = str(tile.get("crop", "")).upper()
                if a == "COW": cow_count += 1
                elif a == "SHEEP": sheep_count += 1
                if c == "STRAWBERRY": straw_count += 1
                elif c in ("WHEAT", "CARROT", "TOMATO", "MELON"): other_crop_count += 1

        # Sample at day boundaries
        if step_idx % 24 == 0 or step_idx == 719:
            timeline["lands_by_day"][f"D{day}"] = quadrants
            timeline["workers_by_day"][f"D{day}"] = hands
            timeline["cows_by_day"][f"D{day}"] = cow_count
            timeline["sheep_by_day"][f"D{day}"] = sheep_count
            timeline["strawberries_by_day"][f"D{day}"] = straw_count
            timeline["other_crops_by_day"][f"D{day}"] = other_crop_count
            timeline["cash_by_day"][f"D{day}"] = money

        # Track purchases & investments
        act = state.get("action") or {}
        if isinstance(act, dict):
            for m in act.get("market") or []:
                if isinstance(m, list) and len(m) >= 2:
                    cmd = m[0]
                    if cmd == "BUY_SEED":
                        timeline["last_buy_seed_step"] = step_idx
                    elif cmd == "BUY_ANIMAL":
                        timeline["last_buy_animal_step"] = step_idx
                    elif cmd == "HIRE":
                        timeline["last_hire_step"] = step_idx
                    elif cmd == "SELL" and len(m) >= 3:
                        item = m[1]
                        qty = float(m[2])
                        timeline["sales_by_commodity"][item] += qty
                        if 10 <= day <= 25:
                            timeline["sales_cadence_days_10_25"] += 1

    timeline["total_quadrants"] = max(timeline["lands_by_day"].values()) if timeline["lands_by_day"] else 1
    timeline["total_workers"] = max(timeline["workers_by_day"].values()) if timeline["workers_by_day"] else 1
    timeline["total_cows"] = max(timeline["cows_by_day"].values()) if timeline["cows_by_day"] else 0
    timeline["total_sheep"] = max(timeline["sheep_by_day"].values()) if timeline["sheep_by_day"] else 0
    timeline["terminal_bank"] = money

    return timeline

def main():
    print("=" * 125)
    print("EXP117: POST-DAY 10 ELITE MACRO SEPARATION & ARCHITECTURAL MINING")
    print("=" * 125)

    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[['episode_id', 'seed', 'elo_avg']], on='episode_id')

    # Selected Elite Clusters vs Hostile Squeeze Clusters
    clusters_to_mine = {
        "Cluster 87 (96.3% WR | $120.2k Mean)": 87,
        "Cluster 59 (88.1% WR | $96.8k Mean)": 59,
        "Cluster 84 (86.2% WR | $96.2k Mean)": 84,
        "Cluster 73 (80.6% WR | $97.2k Mean)": 73,
        "Cluster 76 (100.0% WR| $74.0k Mean)": 76,
        "Cluster 8  (Squeeze  | $116.5k Opponent)": 8,
        "Cluster 19 (Hostile  | 24.3% WR)": 19,
    }

    cluster_profiles = {}

    for label, cluster_id in clusters_to_mine.items():
        subset = df_merged[df_merged['cluster'] == cluster_id]
        print(f"\n--- Mining {label} ({len(subset)} seats in corpus) ---")

        timelines = []
        for _, row in subset.head(8).iterrows():
            ep_id = int(row['episode_id'])
            seat = int(row['seat'])
            ep_path = get_episode_path(ep_id)
            if not ep_path:
                continue
            tl = analyze_episode_post_day10(ep_path, seat)
            if tl:
                timelines.append(tl)

        if not timelines:
            print("  No replays successfully parsed.")
            continue

        # Aggregate metrics
        n = len(timelines)
        avg_quads = np.mean([t["total_quadrants"] for t in timelines])
        avg_workers = np.mean([t["total_workers"] for t in timelines])
        avg_cows = np.mean([t["total_cows"] for t in timelines])
        avg_sheep = np.mean([t["total_sheep"] for t in timelines])
        avg_terminal = np.mean([t["terminal_bank"] for t in timelines])
        avg_last_seed_day = np.mean([t["last_buy_seed_step"] // 24 for t in timelines])
        avg_last_animal_day = np.mean([t["last_buy_animal_step"] // 24 for t in timelines])
        avg_last_hire_day = np.mean([t["last_hire_step"] // 24 for t in timelines])
        avg_mid_sales_cadence = np.mean([t["sales_cadence_days_10_25"] for t in timelines])

        # Strawberries at Day 10, 15, 20, 25
        straw_d10 = np.mean([t["strawberries_by_day"].get("D10", 0) for t in timelines])
        straw_d15 = np.mean([t["strawberries_by_day"].get("D15", 0) for t in timelines])
        straw_d20 = np.mean([t["strawberries_by_day"].get("D20", 0) for t in timelines])
        straw_d25 = np.mean([t["strawberries_by_day"].get("D25", 0) for t in timelines])

        # Other crops at Day 10, 15, 20
        other_d10 = np.mean([t["other_crops_by_day"].get("D10", 0) for t in timelines])
        other_d15 = np.mean([t["other_crops_by_day"].get("D15", 0) for t in timelines])
        other_d20 = np.mean([t["other_crops_by_day"].get("D20", 0) for t in timelines])

        # Cash at Day 10, 15, 20, 25
        cash_d10 = np.mean([t["cash_by_day"].get("D10", 0) for t in timelines])
        cash_d15 = np.mean([t["cash_by_day"].get("D15", 0) for t in timelines])
        cash_d20 = np.mean([t["cash_by_day"].get("D20", 0) for t in timelines])
        cash_d25 = np.mean([t["cash_by_day"].get("D25", 0) for t in timelines])

        # Top sold commodities
        sales_summary = defaultdict(float)
        for t in timelines:
            for item, qty in t["sales_by_commodity"].items():
                sales_summary[item] += qty / n
        top_sales = sorted(sales_summary.items(), key=lambda x: x[1], reverse=True)[:4]
        top_sales_str = ", ".join(f"{k}:{v:,.0f}" for k, v in top_sales)

        cluster_profiles[label] = {
            "quads": avg_quads,
            "workers": avg_workers,
            "cows": avg_cows,
            "sheep": avg_sheep,
            "terminal": avg_terminal,
            "last_seed_day": avg_last_seed_day,
            "last_animal_day": avg_last_animal_day,
            "last_hire_day": avg_last_hire_day,
            "straw_curve": (straw_d10, straw_d15, straw_d20, straw_d25),
            "other_curve": (other_d10, other_d15, other_d20),
            "cash_curve": (cash_d10, cash_d15, cash_d20, cash_d25),
            "top_sales": top_sales_str,
            "mid_sales_cadence": avg_mid_sales_cadence,
        }

        print(f"  * Peak Quadrants: {avg_quads:.1f} | Peak Workers: {avg_workers:.1f}")
        print(f"  * Peak Livestock: {avg_cows:.1f} Cows, {avg_sheep:.1f} Sheep")
        print(f"  * Reinvestment Cutoffs -> Last Seed: Day {avg_last_seed_day:.1f} | Last Animal: Day {avg_last_animal_day:.1f} | Last Hire: Day {avg_last_hire_day:.1f}")
        print(f"  * Strawberry Footprint: D10={straw_d10:.1f}, D15={straw_d15:.1f}, D20={straw_d20:.1f}, D25={straw_d25:.1f}")
        print(f"  * Other Crops Footprint: D10={other_d10:.1f}, D15={other_d15:.1f}, D20={other_d20:.1f}")
        print(f"  * Cash Curve: D10=${cash_d10:,.0f}, D15=${cash_d15:,.0f}, D20=${cash_d20:,.0f}, D25=${cash_d25:,.0f}")
        print(f"  * Top Sales Volume: [{top_sales_str}]")
        print(f"  * Mid-Game Sales Cadence (Days 10-25): {avg_mid_sales_cadence:.1f} sales events")

    # Compare against D.1 Baseline
    print("\n" + "=" * 125)
    print("MACRO STRUCTURAL COMPARISON: D.1 BASELINE vs TOP ELITE CLUSTERS")
    print("=" * 125)
    print(f"{'Archetype / Cluster':<40s} | {'Quads':<5s} | {'Hands':<5s} | {'Cows':<5s} | {'Sheep':<5s} | {'Last Seed':<9s} | {'Last Hire':<9s} | {'D15 Cash':<10s} | {'D20 Cash':<10s}")
    print("-" * 125)
    print(f"{'Variant D.1 (Control A Baseline)':<40s} | {'3.0':<5s} | {'13.0':<5s} | {'8.0':<5s} | {'0.0':<5s} | {'Day 18.0':<9s} | {'Day 12.0':<9s} | {'~$4,500':<10s} | {'~$25,000':<10s}")

    for label, p in cluster_profiles.items():
        print(f"{label[:40]:<40s} | {p['quads']:<5.1f} | {p['workers']:<5.1f} | {p['cows']:<5.1f} | {p['sheep']:<5.1f} | Day {p['last_seed_day']:<5.1f} | Day {p['last_hire_day']:<5.1f} | ${p['cash_curve'][1]:<9,.0f} | ${p['cash_curve'][2]:<9,.0f}")

    print("=" * 125)

if __name__ == "__main__":
    main()
