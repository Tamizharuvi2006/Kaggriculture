"""EXP072: Live Match Telemetry & Opponent Forensic Analyzer for Variant D.1 (Ref: 55780289).

1. Fetches all tournament matches played by submission 55780289 from Kaggle API.
2. Computes aggregate win rate, Elo trajectory, opponent rating distribution, and coin margins.
3. Identifies specific opponents responsible for losses.
4. Downloads replay telemetry for all loss matches to pinpoint exact loss mechanisms.
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
SUB_ID = 55780289
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_headers():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def fetch_d1_episodes():
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(SUB_ID)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        print(f"Error fetching episodes: {e}")
        return []

def fetch_episode_detail(ep_id: int):
    cache_file = os.path.join(OUTPUT_DIR, f"episode_{ep_id}.json")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    headers = get_headers()
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f"Failed to fetch episode {ep_id}: {e}")
        return None

def analyze_d1_telemetry():
    print("=" * 105)
    print(f"EXP072: LIVE TELEMETRY & OPPONENT AUDIT FOR VARIANT D.1 (SUBMISSION {SUB_ID})")
    print("=" * 105)

    episodes = fetch_d1_episodes()
    print(f"Retrieved {len(episodes)} completed live ladder matches from Kaggle API.")

    if not episodes:
        print("No matches played yet. The submission may still be queued or in initial warmup.")
        return

    parsed_matches = []
    for ep in episodes:
        agents = ep.get("agents", [])
        if len(agents) < 2:
            continue

        our_ag = next((a for a in agents if a.get("submissionId") == SUB_ID), None)
        opp_ag = next((a for a in agents if a.get("submissionId") != SUB_ID), None)

        if not our_ag or not opp_ag:
            continue

        our_reward = float(our_ag.get("reward") or 0.0)
        opp_reward = float(opp_ag.get("reward") or 0.0)
        our_score_init = float(our_ag.get("initialScore") or 0.0)
        our_score_after = float(our_ag.get("updatedScore") or 0.0)
        opp_score_init = float(opp_ag.get("initialScore") or 0.0)
        opp_sub_id = opp_ag.get("submissionId")
        ep_id = ep.get("id")
        created_time = ep.get("createTime", "")

        is_win = 1 if our_reward > opp_reward else 0
        is_loss = 1 if our_reward < opp_reward else 0
        is_tie = 1 if our_reward == opp_reward else 0

        parsed_matches.append({
            "ep_id": ep_id,
            "date": created_time,
            "our_reward": our_reward,
            "opp_reward": opp_reward,
            "margin": our_reward - opp_reward,
            "our_score_init": our_score_init,
            "our_score_after": our_score_after,
            "opp_score_init": opp_score_init,
            "opp_sub_id": opp_sub_id,
            "is_win": is_win,
            "is_loss": is_loss,
            "is_tie": is_tie,
        })

    # Sort chronologically
    parsed_matches.sort(key=lambda x: x["ep_id"])

    total = len(parsed_matches)
    wins = sum(m["is_win"] for m in parsed_matches)
    losses = sum(m["is_loss"] for m in parsed_matches)
    ties = sum(m["is_tie"] for m in parsed_matches)
    win_rate = wins / total if total > 0 else 0

    print(f"\n1. AGGREGATE PERFORMANCE METRICS")
    print("-" * 105)
    print(f"Total Matches Played : {total}")
    print(f"Record               : {wins} Wins / {losses} Losses / {ties} Ties")
    print(f"Win Rate             : {win_rate:.1%}")
    if parsed_matches:
        print(f"Current Live Score   : {parsed_matches[-1]['our_score_after']:.1f}")
        print(f"Peak Live Score      : {max(m['our_score_after'] for m in parsed_matches):.1f}")
        print(f"Lowest Live Score    : {min(m['our_score_after'] for m in parsed_matches):.1f}")
        print(f"Mean D.1 Reward ($)  : ${np.mean([m['our_reward'] for m in parsed_matches]):,.2f}")
        print(f"Mean Opp Reward ($)  : ${np.mean([m['opp_reward'] for m in parsed_matches]):,.2f}")
        print(f"Mean Net Margin ($)  : ${np.mean([m['margin'] for m in parsed_matches]):+,.2f}")

    print("\n" + "=" * 105)
    print("2. CHRONOLOGICAL MATCH HISTORY TABLE")
    print("=" * 105)
    print(f"{'Ep ID':<10} | {'Opp Sub ID':<11} | {'Opp Rating':>10} | {'D.1 Reward':>11} | {'Opp Reward':>11} | {'Margin ($)':>11} | {'Rating Delta':>12} | {'Result'}")
    print("-" * 105)

    for m in parsed_matches:
        res_str = "WIN" if m["is_win"] else ("LOSS" if m["is_loss"] else "TIE")
        r_delta = m["our_score_after"] - m["our_score_init"]
        print(f"{m['ep_id']:<10} | {str(m['opp_sub_id']):<11} | {m['opp_score_init']:>10.1f} | ${m['our_reward']:>10,.0f} | ${m['opp_reward']:>10,.0f} | ${m['margin']:>+10,.0f} | {r_delta:>+11.1f} | {res_str}")

    print("=" * 105)

    # Group by Opponent
    by_opp = {}
    for m in parsed_matches:
        o_id = m["opp_sub_id"]
        by_opp.setdefault(o_id, []).append(m)

    print("\n" + "=" * 105)
    print("3. OPPONENT CLUSTER BREAKDOWN (WHO IS BEATING D.1?)")
    print("=" * 105)
    print(f"{'Opponent Sub ID':<16} | {'Opp Avg Rating':>14} | {'Matches':>8} | {'D.1 Wins':>9} | {'D.1 Losses':>10} | {'Win Rate %':>11} | {'Avg Margin ($)'}")
    print("-" * 105)

    sorted_opps = sorted(by_opp.items(), key=lambda kv: (sum(m['is_loss'] for m in kv[1]), -np.mean([m['opp_score_init'] for m in kv[1]])), reverse=True)
    for o_id, o_matches in sorted_opps:
        o_wins = sum(m["is_win"] for m in o_matches)
        o_losses = sum(m["is_loss"] for m in o_matches)
        o_wr = o_wins / len(o_matches)
        avg_rating = np.mean([m["opp_score_init"] for m in o_matches])
        avg_marg = np.mean([m["margin"] for m in o_matches])
        print(f"{str(o_id):<16} | {avg_rating:>14.1f} | {len(o_matches):>8} | {o_wins:>9} | {o_losses:>10} | {o_wr:>10.1%} | ${avg_marg:>+13,.0f}")

    print("=" * 105)

    # Download and analyze all loss episodes
    loss_matches = [m for m in parsed_matches if m["is_loss"]]
    if loss_matches:
        print(f"\nDownloading detailed replay JSONs for all {len(loss_matches)} loss matches...")
        enriched_losses = []
        for lm in loss_matches:
            rep = fetch_episode_detail(lm["ep_id"])
            if rep:
                ep_info = rep.get("episode", {})
                seed = ep_info.get("seed")
                lm["seed"] = seed
                enriched_losses.append(lm)
                print(f"  -> Episode {lm['ep_id']} (Opp Sub {lm['opp_sub_id']}): Seed = {seed}, Margin = ${lm['margin']:,.0f}")

        # Save summary report
        summary_file = os.path.join(OUTPUT_DIR, "d1_telemetry_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({
                "submission_id": SUB_ID,
                "total_matches": total,
                "record": {"wins": wins, "losses": losses, "ties": ties, "win_rate": win_rate},
                "matches": parsed_matches,
                "losses": enriched_losses
            }, f, indent=2)
        print(f"\nSummary saved to {summary_file}")

if __name__ == "__main__":
    analyze_d1_telemetry()
