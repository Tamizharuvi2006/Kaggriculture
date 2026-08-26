"""EXP076: Deep Forensic Reverse-Engineering of 3011.4-Elo Grandmaster Replays.

Parses downloaded step-by-step match replays for Submission 55396329 (3011.4 Elo):
1. Day-by-day asset progression (Land, Crops, Cows, Workers, Cash)
2. Exact crop distribution (Strawberries vs Melons vs Carrots)
3. Worker allocation & watering discipline
4. Market selling strategy & price realization
5. Direct architectural comparison: 3011.4 Grandmaster vs Variant D.1
"""
from __future__ import annotations
import sys
import os
import json
import glob
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAY_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "grandmaster_replays")

def analyze_grandmaster_replays():
    files = glob.glob(os.path.join(REPLAY_DIR, "gm_episode_*.json"))
    print(f"Loaded {len(files)} downloaded Grandmaster replays for forensic reconstruction.")

    if not files:
        print("No replay files found.")
        return

    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        ep = data.get("episode", {})
        ep_id = ep.get("id")
        seed = ep.get("seed")
        agents = ep.get("agents", [])
        steps = data.get("steps", [])

        print("\n" + "=" * 105)
        print(f"FORENSIC INSPECTION: EPISODE {ep_id} (Seed: {seed})")
        print("=" * 105)

        for idx, a in enumerate(agents):
            sub_id = a.get("submissionId")
            score = float(a.get("initialScore") or 0.0)
            rew = float(a.get("reward") or 0.0)
            print(f"  Player {idx}: Submission {sub_id} | Rating: {score:.1f} | Final Reward: ${rew:,.2f}")

        # Check step details
        if not steps:
            print("  Note: Step actions not included in standard API payload, inspecting metadata.")
            continue

        print(f"  Total Steps in Replay: {len(steps)}")

    print("\n" + "=" * 105)
    print("EPISODE SUMMARY TABLE")
    print("=" * 105)

if __name__ == "__main__":
    analyze_grandmaster_replays()
