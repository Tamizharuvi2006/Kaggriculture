"""Download and analyze all live Kaggle tournament matches for all our submissions using Kaggle EpisodeService API.
"""

from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error
import numpy as np
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = r"D:\kaggriculture"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports", "live_match_telemetry")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"

def get_headers():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def fetch_all_our_submissions():
    headers = get_headers()
    url = "https://www.kaggle.com/api/v1/competitions/submissions/list/kaggriculture"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_episodes_for_submission(sub_id: int):
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(sub_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        print(f"Error fetching episodes for submission {sub_id}: {e}")
        return []

def main():
    print("=" * 100)
    print("📥 DOWNLOADING ALL LIVE KAGGLE TOURNAMENT MATCHES FOR ALL SUBMISSIONS")
    print("=" * 100)

    subs = fetch_all_our_submissions()
    print(f"Found {len(subs)} total submissions in competition 'kaggriculture'.\n")

    all_matches_by_sub = {}

    for sub in subs:
        sub_id = sub.get("ref")
        desc = sub.get("description", "")
        score = sub.get("publicScore", "")
        status = sub.get("status", "")

        if not sub_id or status != "complete":
            continue

        print(f"Fetching episodes for Sub {sub_id} ({desc[:50]}... | Score: {score})...", flush=True)
        episodes = fetch_episodes_for_submission(sub_id)
        print(f"  -> Retrieved {len(episodes)} completed tournament matches.")

        sub_file = os.path.join(OUTPUT_DIR, f"submission_{sub_id}_episodes.json")
        with open(sub_file, "w", encoding="utf-8") as f:
            json.dump({"submission": sub, "episodes": episodes}, f, indent=2)

    print("\n✅ All live match episode telemetry downloaded successfully!")

if __name__ == "__main__":
    main()
