"""Inspect all submission descriptions and extract all loss episodes across all 10 submissions."""
import os
import json
import glob

BASE_DIR = r"D:\kaggriculture"
telemetry_dir = os.path.join(BASE_DIR, "reports", "live_match_telemetry")

sub_files = glob.glob(os.path.join(telemetry_dir, "submission_*_episodes.json"))
print(f"Found {len(sub_files)} submission episode metadata files:")

for sf in sub_files:
    with open(sf, "r", encoding="utf-8") as f:
        data = json.load(f)
    sub = data.get("submission", {})
    episodes = data.get("episodes", [])
    sub_id = sub.get("ref", os.path.basename(sf).split("_")[1])
    desc = sub.get("description", "No description")
    score = sub.get("publicScore", "N/A")
    date = sub.get("submittedDate", "N/A")
    
    losses = 0
    wins = 0
    ties = 0
    for ep in episodes:
        agents = ep.get("agents", [])
        if len(agents) >= 2:
            our_ag = next((a for a in agents if a.get("submissionId") == sub_id), None)
            opp_ag = next((a for a in agents if a.get("submissionId") != sub_id), None)
            if our_ag and opp_ag:
                our_r = float(our_ag.get("reward") or 0.0)
                opp_r = float(opp_ag.get("reward") or 0.0)
                if our_r > opp_r: wins += 1
                elif our_r < opp_r: losses += 1
                else: ties += 1

    print(f"\nSubmission ID: {sub_id}")
    print(f"  Description : {desc}")
    print(f"  Public Score: {score} | Date: {date}")
    print(f"  Total Matches: {len(episodes)} (Wins: {wins}, Losses: {losses}, Ties: {ties})")
