"""EXP075: Recursive Grandmaster Match Crawler & 3100-Tier Farm Archaeologist.

1. Crawls Kaggle EpisodeService network starting from known high-tier nodes.
2. Identifies all matches involving 2400-3100+ Elo agents (Crop Dusta, Ryo Hasegawa, Subramanya N, etc.).
3. Downloads step-level episode replays for the highest-rated matches.
4. Reverse-engineers the exact physical, economic, and scheduling fingerprints of the 3100-rated agents:
   - Land purchase timestamps
   - Crop footprint & crop type choices
   - Livestock scaling curves
   - Staffing trajectories (worker count vs step)
   - Market pricing realization
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error
import time
from collections import deque
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "grandmaster_replays")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def fetch_sub_episodes(sub_id: int):
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(sub_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        return []

def fetch_full_episode(ep_id: int):
    cache_file = os.path.join(OUTPUT_DIR, f"gm_episode_{ep_id}.json")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
        try:
            with open(cache_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass

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

def crawl_ladder():
    print("=" * 105)
    print("EXP075: RECURSIVE CRAWLER FOR TOP 2400-3100 TIER GRANDMASTER REPLAYS")
    print("=" * 105)

    # Initial seed submissions (from our high-rated opponents)
    seed_subs = [55309911, 55787488, 55242320, 55291921, 55289065, 55788975]
    queue = deque(seed_subs)
    visited_subs = set()
    high_tier_matches = []
    discovered_gms = {} # sub_id -> max_rating

    print(f"Starting BFS crawl from {len(seed_subs)} seed submission nodes...")

    max_crawls = 30
    crawls = 0

    while queue and crawls < max_crawls:
        curr_sub = queue.popleft()
        if curr_sub in visited_subs:
            continue
        visited_subs.add(curr_sub)
        crawls += 1

        print(f"[{crawls}/{max_crawls}] Querying Sub {curr_sub}...", flush=True)
        episodes = fetch_sub_episodes(curr_sub)
        print(f"  -> Found {len(episodes)} episodes.")

        for ep in episodes:
            agents = ep.get("agents", [])
            for a in agents:
                sub_id = a.get("submissionId")
                score = float(a.get("initialScore") or 0.0)
                if score > 0:
                    if sub_id not in discovered_gms or score > discovered_gms[sub_id]:
                        discovered_gms[sub_id] = score

                if score >= 2000.0 and sub_id not in visited_subs:
                    queue.append(sub_id)

            # Check if this match is high tier (at least one agent >= 2000 Elo)
            max_score_in_ep = max([float(a.get("initialScore") or 0.0) for a in agents] + [0.0])
            if max_score_in_ep >= 2000.0:
                high_tier_matches.append({
                    "ep_id": ep.get("id"),
                    "max_score": max_score_in_ep,
                    "agents": agents,
                })

    # Sort high tier matches by highest Elo
    high_tier_matches.sort(key=lambda x: x["max_score"], reverse=True)
    dedup_matches = {m["ep_id"]: m for m in high_tier_matches}
    sorted_matches = sorted(dedup_matches.values(), key=lambda x: x["max_score"], reverse=True)

    print("\n" + "=" * 105)
    print(f"DISCOVERED {len(discovered_gms)} AGENTS IN CRAWL NETWORK")
    print("=" * 105)
    sorted_gms = sorted(discovered_gms.items(), key=lambda kv: kv[1], reverse=True)
    print(f"{'Submission ID':<16} | {'Peak Observed Elo Rating':>28} | {'Tier Classification'}")
    print("-" * 105)
    for s_id, sc in sorted_gms[:20]:
        tier = "3000+ GRANDMASTER" if sc >= 3000 else ("2500+ MASTER" if sc >= 2500 else ("2000+ ELITE" if sc >= 2000 else "COMPETITIVE"))
        print(f"{s_id:<16} | {sc:>28.1f} | {tier}")

    print("=" * 105)
    print(f"\nDiscovered {len(sorted_matches)} elite 2000-3100 tier match episodes.")

    # Download top 10 highest-tier matches
    downloaded_eps = []
    for m in sorted_matches[:10]:
        ep_id = m["ep_id"]
        print(f"Downloading Replay for Elite Episode {ep_id} (Peak Rating: {m['max_score']:.1f})...", flush=True)
        ep_detail = fetch_full_episode(ep_id)
        if ep_detail:
            downloaded_eps.append({"ep_id": ep_id, "max_score": m["max_score"], "data": ep_detail})

    print(f"\nSuccessfully downloaded {len(downloaded_eps)} elite grandmaster replays for forensic reconstruction.")

if __name__ == "__main__":
    crawl_ladder()
