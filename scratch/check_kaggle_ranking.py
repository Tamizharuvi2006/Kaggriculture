"""Fetch Complete Kaggle Leaderboard Standings for Kaggriculture Competition.
"""

from __future__ import annotations
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    api = KaggleApi()
    api.authenticate()
    leader = api.competition_leaderboard_view('kaggriculture')

    print("==================================================================================", flush=True)
    print("🏆 KAGGRICULTURE LIVE KAGGLE LEADERBOARD STANDINGS", flush=True)
    print("==================================================================================", flush=True)

    tamizh_found = False

    for idx, t in enumerate(leader, start=1):
        team_name = getattr(t, "_team_name", "N/A")
        score = getattr(t, "_score", "N/A")
        if "tamiz" in team_name.lower():
            tamizh_found = True
            print(f"⭐ Rank {idx:3d} | TEAM: {team_name:<30} | PUBLIC SCORE: {score} 🏆", flush=True)
        else:
            print(f"   Rank {idx:3d} | Team: {team_name:<30} | Score: {score}", flush=True)

    if not tamizh_found:
        # Check team submission records
        subs = api.competition_submissions('kaggriculture')
        print("\n--- TEAM SUBMISSION HISTORICAL SCORES ---", flush=True)
        for s in subs:
            ref = getattr(s, "_ref", "N/A")
            fname = getattr(s, "_file_name", "N/A")
            score = getattr(s, "_public_score", "N/A")
            date = getattr(s, "_date", "N/A")
            desc = getattr(s, "_description", "N/A")
            print(f"Ref: {ref} | Score: {score} | File: {fname:<35} | Date: {date} | Desc: {desc}")

    print("==================================================================================", flush=True)

if __name__ == "__main__":
    main()
