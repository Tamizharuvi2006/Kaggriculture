"""EXP074: Top 3100-Tier Leaderboard Hunter & Replay Reverse-Engineering Lab.

1. Fetches the current live Kaggle leaderboard for competition 'kaggriculture'.
2. Identifies top-ranked teams/submissions (ratings 1500-3100+).
3. Fetches recent tournament episodes for top teams via Kaggle API.
4. Downloads full step-level replays and reconstructs the Top Agent Archetype:
   - Day 1-3 Bootstrap & Opening
   - Land expansion trajectory (Land #2, #3, #4 steps)
   - Crop portfolio distribution over time (Strawberries, Melons, Carrots, etc.)
   - Livestock scaling (Cow count vs step)
   - Labor force trajectory (Worker count vs step)
   - Market liquidation strategy & price realization
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "top_tier_replays")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_headers():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def fetch_leaderboard():
    headers = get_headers()
    # Try public leaderboard API
    url = "https://www.kaggle.com/api/v1/competitions/kaggriculture/leaderboard"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching leaderboard via v1 API: {e}")
        return None

def fetch_episodes_for_sub(sub_id: int):
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(sub_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        return []

def fetch_full_episode(ep_id: int):
    cache_file = os.path.join(OUTPUT_DIR, f"top_episode_{ep_id}.json")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
        try:
            with open(cache_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass

    headers = get_headers()
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            return data
    except Exception as e:
        return None

def run_hunter():
    print("=" * 105)
    print("EXP074: HUNTING TOP 3100-TIER LEADERBOARD AGENTS & REPLAYS")
    print("=" * 105)

    lb_data = fetch_leaderboard()
    if not lb_data:
        print("Falling back to Kaggle CLI for leaderboard extraction...")
        import subprocess
        res = subprocess.run(["python", "-m", "kaggle", "competitions", "leaderboard", "-c", "kaggriculture", "--show"], capture_output=True, text=True)
        print("Leaderboard CLI Output:")
        print(res.stdout[:2000])
        return

    print(f"Successfully retrieved leaderboard data.")
    print("Top leaderboard structure:", type(lb_data))

if __name__ == "__main__":
    run_hunter()
