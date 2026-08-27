"""EXP094: 24-Hour Live Ladder Telemetry Audit & Temporal Bisection.

Fetches the complete up-to-date live match corpus for Variant D.1 (Submission: 55780289).
Computes:
1. Global Telemetry: Matches, Wins, Losses, Win Rate, Mean D.1 Bank, Mean Opp Bank, Mean Margin, Total Pie, Market Share.
2. Temporal Bisection Comparison:
   - Baseline Cohort (First 49 Matches)
   - Fresh 24h Cohort (Matches #50 to Present)
3. Opponent Rating Bands:
   - <900 Casual
   - 900-1200 Competitive
   - 1200-2000 Advanced
   - 2000+ Grandmaster
4. Loss Buckets (Micro <= $5k, Moderate $5k-$15k, Large > $15k).
5. Top 10 Largest Deficit Loss Opponents.
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

SUBMISSION_ID = 55780289
API_URL = f"https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes?submissionId={SUBMISSION_ID}"
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches")
SUMMARY_PATH = os.path.join(REPORTS_DIR, "d1_telemetry_summary.json")

def fetch_all_episodes():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            eps = data.get("episodes", [])
            print(f"Successfully fetched {len(eps)} total live episodes from Kaggle API.")
            return eps
    except Exception as e:
        print(f"API Fetch failed: {e}. Checking local cache...")

    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)
            return summary.get("matches", [])
    return []

def analyze_telemetry():
    print("=" * 105)
    print("EXP094: 24-HOUR LIVE LADDER TELEMETRY AUDIT & TEMPORAL BISECTION")
    print("=" * 105)

    raw_episodes = fetch_all_episodes()
    if not raw_episodes:
        print("No match data found.")
        return

    def get_sort_key(ep):
        return ep.get("id") or ep.get("ep_id") or 0

    sorted_eps = sorted(raw_episodes, key=get_sort_key)

    parsed_matches = []
    for idx, ep in enumerate(sorted_eps):
        ep_id = ep.get("id") or ep.get("ep_id")
        seed = ep.get("seed")
        agents = ep.get("agents", [])

        if len(agents) >= 2:
            if agents[0].get("submissionId") == SUBMISSION_ID:
                d1 = agents[0]
                opp = agents[1]
            else:
                d1 = agents[1]
                opp = agents[0]

            d1_reward = float(d1.get("reward") or 0.0)
            opp_reward = float(opp.get("reward") or 0.0)
            opp_elo = float(opp.get("initialScore") or 1000.0)
            d1_elo = float(d1.get("initialScore") or 1000.0)
            d1_final_score = float(d1.get("updatedScore") or d1_elo)
            opp_sub_id = opp.get("submissionId")
        else:
            d1_reward = float(ep.get("d1_reward") or 0.0)
            opp_reward = float(ep.get("opp_reward") or 0.0)
            opp_elo = float(ep.get("opp_score_init") or 1000.0)
            d1_elo = float(ep.get("d1_score_init") or 1000.0)
            d1_final_score = float(ep.get("d1_score_final") or d1_elo)
            opp_sub_id = ep.get("opp_sub_id")

        margin = d1_reward - opp_reward
        total_pie = d1_reward + opp_reward
        d1_share = (d1_reward / total_pie) if total_pie > 0 else 0.0
        won = d1_reward > opp_reward

        # Loss bucket
        if won:
            loss_bucket = "VICTORY"
        else:
            abs_def = abs(margin)
            if abs_def <= 5000:
                loss_bucket = "MICRO"
            elif abs_def <= 15000:
                loss_bucket = "MODERATE"
            else:
                loss_bucket = "LARGE"

        # Rating band
        if opp_elo < 900:
            band = "<900 (Casual)"
        elif opp_elo <= 1200:
            band = "900-1200 (Competitive)"
        elif opp_elo <= 2000:
            band = "1200-2000 (Advanced)"
        else:
            band = "2000+ (Elite GM)"

        parsed_matches.append({
            "idx": idx + 1,
            "ep_id": ep_id,
            "seed": seed,
            "opp_sub": opp_sub_id,
            "won": won,
            "d1_reward": d1_reward,
            "opp_reward": opp_reward,
            "margin": margin,
            "total_pie": total_pie,
            "d1_share": d1_share,
            "d1_elo": d1_elo,
            "opp_elo": opp_elo,
            "d1_final_score": d1_final_score,
            "loss_bucket": loss_bucket,
            "band": band,
        })

    total_count = len(parsed_matches)
    wins = sum(1 for m in parsed_matches if m["won"])
    losses = total_count - wins
    latest_score = parsed_matches[-1]["d1_final_score"] if parsed_matches else 929.5

    print(f"\n1. GLOBAL TELEMETRY OVERVIEW ({total_count} TOTAL MATCHES):")
    print("-" * 105)
    print(f"  * Record             : {wins} Wins / {losses} Losses ({wins/total_count:.1%} Win Rate)")
    print(f"  * Latest Live Rating : {latest_score:.1f} Elo")
    print(f"  * Mean D.1 Bank      : ${np.mean([m['d1_reward'] for m in parsed_matches]):>10,.2f}")
    print(f"  * Mean Opponent Bank : ${np.mean([m['opp_reward'] for m in parsed_matches]):>10,.2f}")
    print(f"  * Mean Net Margin    : ${np.mean([m['margin'] for m in parsed_matches]):>+10,.2f}")
    print(f"  * Mean Shared Pie    : ${np.mean([m['total_pie'] for m in parsed_matches]):>10,.2f}")
    print(f"  * Mean Market Share  : {np.mean([m['d1_share'] for m in parsed_matches]):>9.1%} of Shared Economy")

    # 2. Temporal Bisection (First 49 vs New 24h Matches)
    first_49 = parsed_matches[:49]
    new_matches = parsed_matches[49:]

    print("\n2. TEMPORAL BISECTION (FIRST 49 MATCHES VS FRESH 24-HOUR MATCHES):")
    print("-" * 105)
    print(f"{'Cohort Metric':<28} | {'First 49 Matches':>20} | {'New 24h Matches (' + str(len(new_matches)) + ')':>22} | {'Net Change'}")
    print("-" * 105)

    def summarize_cohort(c):
        if not c:
            return {"count": 0, "wr": 0.0, "d1_bank": 0.0, "opp_bank": 0.0, "margin": 0.0, "pie": 0.0, "share": 0.0, "large": 0}
        n = len(c)
        w = sum(1 for m in c if m["won"])
        return {
            "count": n,
            "wr": w / n,
            "d1_bank": np.mean([m["d1_reward"] for m in c]),
            "opp_bank": np.mean([m["opp_reward"] for m in c]),
            "margin": np.mean([m["margin"] for m in c]),
            "pie": np.mean([m["total_pie"] for m in c]),
            "share": np.mean([m["d1_share"] for m in c]),
            "large": sum(1 for m in c if m["loss_bucket"] == "LARGE"),
        }

    s1 = summarize_cohort(first_49)
    s2 = summarize_cohort(new_matches)

    if s2["count"] > 0:
        print(f"{'Match Count':<28} | {s1['count']:>20} | {s2['count']:>22} | {s2['count'] - s1['count']:>+10}")
        print(f"{'Win Rate (%)':<28} | {s1['wr']:>19.1%} | {s2['wr']:>21.1%} | {s2['wr'] - s1['wr']:>+9.1%}")
        print(f"{'Mean D.1 Bank ($)':<28} | ${s1['d1_bank']:>19,.2f} | ${s2['d1_bank']:>21,.2f} | ${s2['d1_bank'] - s1['d1_bank']:>+9,.2f}")
        print(f"{'Mean Opponent Bank ($)':<28} | ${s1['opp_bank']:>19,.2f} | ${s2['opp_bank']:>21,.2f} | ${s2['opp_bank'] - s1['opp_bank']:>+9,.2f}")
        print(f"{'Mean Net Margin ($)':<28} | ${s1['margin']:>19,.2f} | ${s2['margin']:>21,.2f} | ${s2['margin'] - s1['margin']:>+9,.2f}")
        print(f"{'Mean Economic Pie ($)':<28} | ${s1['pie']:>19,.2f} | ${s2['pie']:>21,.2f} | ${s2['pie'] - s1['pie']:>+9,.2f}")
        print(f"{'Mean Market Share (%)':<28} | {s1['share']:>19.1%} | {s2['share']:>21.1%} | {s2['share'] - s1['share']:>+9.1%}")
        print(f"{'Large-Margin Losses (> $15k)':<28} | {s1['large']:>20} | {s2['large']:>22} | {s2['large']:>+10}")
    else:
        print("  * No new matches played in the last 24 hours (Match count remains at 49).")

    # 3. Opponent Rating Bands
    print("\n3. OPPONENT RATING BAND BREAKDOWN (ALL " + str(total_count) + " MATCHES):")
    print("-" * 105)
    print(f"{'Rating Band':<25} | {'Matches':>7} | {'Win Rate':>9} | {'Mean D.1 Bank':>14} | {'Mean Opp Bank':>14} | {'Mean Share %':>12}")
    print("-" * 105)

    for band_name in ["<900 (Casual)", "900-1200 (Competitive)", "1200-2000 (Advanced)", "2000+ (Elite GM)"]:
        subset = [m for m in parsed_matches if m["band"] == band_name]
        if subset:
            n = len(subset)
            w = sum(1 for m in subset if m["won"])
            print(f"{band_name:<25} | {n:>7} | {w/n:>8.1%} | ${np.mean([m['d1_reward'] for m in subset]):>13,.0f} | ${np.mean([m['opp_reward'] for m in subset]):>13,.0f} | {np.mean([m['d1_share'] for m in subset]):>11.1%}")

    # 4. Loss Buckets Breakdown
    loss_matches = [m for m in parsed_matches if not m["won"]]
    print("\n4. LOSS BUCKET TAXONOMY (TOTAL " + str(len(loss_matches)) + " LOSSES):")
    print("-" * 105)
    print(f"  * MICRO-MARGIN (<= $5,000 Deficit)   : {sum(1 for m in loss_matches if m['loss_bucket'] == 'MICRO'):>2} / {len(loss_matches)} ({sum(1 for m in loss_matches if m['loss_bucket'] == 'MICRO')/len(loss_matches):.1%}) -- Duopoly Settlement Noise")
    print(f"  * MODERATE-MARGIN ($5k-$15k Deficit) : {sum(1 for m in loss_matches if m['loss_bucket'] == 'MODERATE'):>2} / {len(loss_matches)} ({sum(1 for m in loss_matches if m['loss_bucket'] == 'MODERATE')/len(loss_matches):.1%}) -- Tight Compounding Swings")
    print(f"  * LARGE-MARGIN (> $15,000 Deficit)   : {sum(1 for m in loss_matches if m['loss_bucket'] == 'LARGE'):>2} / {len(loss_matches)} ({sum(1 for m in loss_matches if m['loss_bucket'] == 'LARGE')/len(loss_matches):.1%}) -- Asymmetric Commodity Opponents")

    # 5. Top 10 Largest Deficit Loss Opponents
    sorted_losses = sorted(loss_matches, key=lambda m: m["margin"])
    print("\n5. TOP 10 LARGEST DEFICIT LOSS OPPONENTS:")
    print("-" * 105)
    print(f"{'Ep ID':<10} | {'Seed':<11} | {'Opp Sub ID':>10} | {'Opp Elo':>8} | {'D.1 Bank ($)':>12} | {'Opp Bank ($)':>12} | {'Deficit ($)':>12} | {'Loss Bucket'}")
    print("-" * 105)

    for l in sorted_losses[:10]:
        seed_str = str(l.get("seed") or "N/A")
        print(f"{l['ep_id']:<10} | {seed_str:<11} | {str(l['opp_sub']):>10} | {l['opp_elo']:>8.1f} | ${l['d1_reward']:>11,.0f} | ${l['opp_reward']:>11,.0f} | ${l['margin']:>+11,.0f} | {l['loss_bucket']}")

    print("=" * 105)

if __name__ == "__main__":
    analyze_telemetry()
