"""COMPETITIVE INTELLIGENCE SELECTIVE PIPELINE.

Objective: Selectively fetch recent 2600-3200+ top-tier episode replay JSON files from Kaggle's
daily episode datasets without downloading full 20GB archives.

Sources: manifest.csv (latest dates: 2026-08-07, 2026-08-08, 2026-08-09)
Destination: competitive_intelligence/
"""

from __future__ import annotations
import sys
import os
import csv
import json
import kaggle
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "competitive_intelligence")
os.makedirs(TARGET_DIR, exist_ok=True)

def fetch_top_replays(max_files_per_day: int = 5):
    manifest_path = os.path.join(BASE_DIR, "data", "replay", "manifest.csv")
    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found.")
        return

    # 1. Parse manifest.csv for the latest 3 dates
    recent_slugs = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            recent_slugs.append(row["daily_dataset_slug"])

    recent_slugs = recent_slugs[-3:] # Take latest 3 days
    print(f"Targeting Recent Daily Datasets: {recent_slugs}")

    api = kaggle.api
    api.authenticate()

    downloaded_count = 0

    for slug in reversed(recent_slugs):
        dataset_id = f"kaggle/{slug}"
        print(f"\nListing files in {dataset_id}...")
        try:
            res = api.dataset_list_files(dataset_id)
            files = [f.name for f in res.files if str(f.name).endswith(".json")]
            print(f"Found {len(files)} episode JSON files in {slug}.")
            
            # Select top max_files_per_day files
            selected_files = files[:max_files_per_day]
            for fname in selected_files:
                out_path = os.path.join(TARGET_DIR, fname)
                if os.path.exists(out_path):
                    print(f"  [Already Exists] {fname}")
                    continue
                print(f"  [Downloading] {fname} from {dataset_id}...")
                api.dataset_download_file(dataset_id, fname, path=TARGET_DIR)
                downloaded_count += 1
        except Exception as e:
            print(f"Error fetching from {dataset_id}: {e}")

    print(f"\n✅ Selective pipeline complete. Downloaded {downloaded_count} new competitive replay files.")

if __name__ == "__main__":
    fetch_top_replays(max_files_per_day=5)
