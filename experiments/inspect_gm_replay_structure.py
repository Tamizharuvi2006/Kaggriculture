"""EXP079: Step-by-Step State & First-Divergence Trajectory Inspector.

Loads Grandmaster replay files and inspects available step fields, observation records, and action logs.
"""
from __future__ import annotations
import sys
import os
import json
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAY_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "grandmaster_replays")

files = glob.glob(os.path.join(REPLAY_DIR, "gm_episode_*.json"))
print(f"Discovered {len(files)} Grandmaster episode files:")

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    ep = data.get("episode", {})
    ep_id = ep.get("id")
    seed = ep.get("seed")
    agents = ep.get("agents", [])
    keys = list(data.keys())
    ep_keys = list(ep.keys())
    print(f"\nEpisode {ep_id} (Seed: {seed}): Root keys: {keys}, Episode keys: {ep_keys}")
    for a in agents:
        print(f"  - Sub ID: {a.get('submissionId')}, Score: {a.get('initialScore')}, Reward: {a.get('reward')}")
