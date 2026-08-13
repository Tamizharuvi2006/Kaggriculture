"""
Download and analyze all live Kaggle tournament matches for all our submissions using Kaggle EpisodeService API.
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

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports", "live_match_telemetry")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TOKEN_PATH = r"C:\Users\43731140\.kaggle\access_token"

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
    master_match_records = []

    for sub in subs:
        sub_id = sub.get("ref")
        desc = sub.get("description", "")
        score = sub.get("publicScore", "")
        status = sub.get("status", "")
        date = sub.get("date", "")

        if not sub_id or status != "complete":
            continue

        print(f"Fetching episodes for Sub {sub_id} ({desc[:50]}... | Score: {score})...", flush=True)
        episodes = fetch_episodes_for_submission(sub_id)
        print(f"  -> Retrieved {len(episodes)} completed tournament matches.")

        all_matches_by_sub[sub_id] = {
            "sub_info": sub,
            "episodes": episodes
        }

        # Save raw JSON
        sub_file = os.path.join(OUTPUT_DIR, f"submission_{sub_id}_episodes.json")
        with open(sub_file, "w", encoding="utf-8") as f:
            json.dump({"submission": sub, "episodes": episodes}, f, indent=2)

        # Parse match statistics
        for ep in episodes:
            ep_id = ep.get("id")
            ctime = ep.get("createTime")
            agents = ep.get("agents", [])
            if len(agents) < 2:
                continue

            our_agent = None
            opp_agent = None
            for ag in agents:
                if ag.get("submissionId") == sub_id:
                    our_agent = ag
                else:
                    opp_agent = ag

            if our_agent and opp_agent:
                our_reward = float(our_agent.get("reward", 0) or 0)
                opp_reward = float(opp_agent.get("reward", 0) or 0)
                our_init_score = float(our_agent.get("initialScore", 0) or 0)
                our_updated_score = float(our_agent.get("updatedScore", 0) or 0)
                opp_init_score = float(opp_agent.get("initialScore", 0) or 0)
                opp_updated_score = float(opp_agent.get("updatedScore", 0) or 0)

                is_win = (our_reward > opp_reward)
                margin = our_reward - opp_reward

                master_match_records.append({
                    "sub_id": sub_id,
                    "sub_desc": desc,
                    "ep_id": ep_id,
                    "create_time": ctime,
                    "our_reward": our_reward,
                    "opp_reward": opp_reward,
                    "is_win": is_win,
                    "margin": margin,
                    "our_init_score": our_init_score,
                    "our_updated_score": our_updated_score,
                    "opp_sub_id": opp_agent.get("submissionId"),
                    "opp_team_id": opp_agent.get("teamId"),
                    "opp_init_score": opp_init_score,
                    "opp_updated_score": opp_updated_score,
                })

    print("\n" + "=" * 100)
    print("📊 LIVE TOURNAMENT PERFORMANCE SUMMARY ACROSS ALL SUBMISSIONS")
    print("=" * 100)

    # Summarize per submission
    lines = []
    lines.append("# 📜 Live Kaggle Tournament Match Telemetry Report")
    lines.append("")
    lines.append(f"> **Report Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"> **Total Live Matches Ingested**: {len(master_match_records)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🏆 1. Live Performance Summary by Submission")
    lines.append("")
    lines.append("| Submission Ref | Description | Score | Live Matches | Wins | Losses | Win Rate | Mean Wealth ($) | Mean Opp Wealth ($) | Mean Margin ($) |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for sub_id, data in all_matches_by_sub.items():
        sub_info = data["sub_info"]
        episodes = data["episodes"]
        sub_matches = [m for m in master_match_records if m["sub_id"] == sub_id]

        if not sub_matches:
            continue

        wins = sum(1 for m in sub_matches if m["is_win"])
        losses = len(sub_matches) - wins
        win_rate = (wins / len(sub_matches) * 100.0) if sub_matches else 0.0

        avg_our_reward = np.mean([m["our_reward"] for m in sub_matches])
        avg_opp_reward = np.mean([m["opp_reward"] for m in sub_matches])
        avg_margin = np.mean([m["margin"] for m in sub_matches])

        score_str = str(sub_info.get("publicScore", "N/A"))
        desc_str = sub_info.get("description", "")[:55]

        print(f"Sub {sub_id:8d} ({score_str:>6s} Elo | {desc_str:<55s}): {wins:2d}W / {losses:2d}L ({win_rate:5.1f}%) | Our: ${avg_our_reward:8.1f} vs Opp: ${avg_opp_reward:8.1f} | Margin: ${avg_margin:+8.1f}")
        lines.append(f"| **{sub_id}** | {desc_str} | **{score_str}** | {len(sub_matches)} | {wins} | {losses} | **{win_rate:.1f}%** | ${avg_our_reward:,.2f} | ${avg_opp_reward:,.2f} | **${avg_margin:+,.2f}** |")

    # APEX 3.3 Specific Deep-Dive
    apex33_matches = [m for m in master_match_records if m["sub_id"] == 55421857]
    if apex33_matches:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 🔬 2. APEX 3.3 Challenger (Ref 55421857) Live Deep-Dive")
        lines.append("")
        lines.append(f"- **Total Live Matches Played**: **{len(apex33_matches)}**")
        a33_wins = sum(1 for m in apex33_matches if m["is_win"])
        lines.append(f"- **Live Win Rate**: **{a33_wins} / {len(apex33_matches)} ({a33_wins / len(apex33_matches) * 100.1:.1f}%)**")
        lines.append(f"- **Mean Realized Wealth**: **${np.mean([m['our_reward'] for m in apex33_matches]):,.2f}**")
        lines.append(f"- **Mean Opponent Wealth**: **${np.mean([m['opp_reward'] for m in apex33_matches]):,.2f}**")
        lines.append(f"- **Mean Margin**: **${np.mean([m['margin'] for m in apex33_matches]):+,.2f}**")
        lines.append("")
        lines.append("### Recent 20 Matches for APEX 3.3:")
        lines.append("")
        lines.append("| Episode ID | Timestamp | Result | Our Wealth ($) | Opp Wealth ($) | Victory Margin ($) | Opponent Sub | Opponent Elo |")
        lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

        for m in sorted(apex33_matches, key=lambda x: x["create_time"], reverse=True)[:20]:
            res_icon = "🏆 WIN" if m["is_win"] else "❌ LOSS"
            time_str = m["create_time"][:16].replace("T", " ")
            lines.append(f"| [{m['ep_id']}](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-{m['ep_id']}) | {time_str} | {res_icon} | ${m['our_reward']:,.1f} | ${m['opp_reward']:,.1f} | **${m['margin']:+,.1f}** | {m['opp_sub_id']} | {m['opp_init_score']:.1f} |")

    report_path = os.path.join(PROJECT_ROOT, "reports", "LIVE_KAGGLE_MATCH_TELEMETRY.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n" + "=" * 100)
    print(f"Report written successfully to: {report_path}")
    print(f"Raw episode JSONs saved in: {OUTPUT_DIR}")
    print("=" * 100)

if __name__ == "__main__":
    main()
