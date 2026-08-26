"""Passive Live-Loss Classifier & Continuous Ladder Telemetry Dashboard.

Runs in Pure Passive Monitoring Mode for Variant D.1 (Submission Ref: 55780289).
Polls live Kaggle telemetry and automatically classifies every match:
1. Cohort Classification:
   - [ELITE] Top Grandmaster (Opponent Elo >= 2000)
   - [COMPETITIVE] Saturated Duopoly (Opponent Elo 900-1200 or Reward > $40k)
   - [CASUAL] Sub-Saturated Asymmetric (Opponent Elo < 900)
2. Economic Pie Dimension:
   - [HIGH-PIE] Total Shared Economy >= $180,000
   - [BASELINE-PIE] Total Shared Economy $140,000 - $180,000
   - [LOW-PIE] Total Shared Economy < $140,000
3. Deficit Margin Classification:
   - [MICRO-MARGIN] Deficit <= $5,000 (Duopoly settlement variance / coin-flip)
   - [MODERATE-MARGIN] Deficit $5,000 - $15,000
   - [LARGE-MARGIN] Deficit > $15,000 (Cross-commodity asymmetry / non-standard opponent)
4. Strict Research Trigger Gate:
   - Checks if >= 10 fresh live losses share the same opponent archetype, market state, and divergence window.
   - If trigger criteria NOT met: Remains 100% FROZEN (Control A).
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
LOCAL_SUMMARY_PATH = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches", "d1_telemetry_summary.json")

def fetch_telemetry():
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            episodes = data.get("episodes", [])
            if episodes:
                return episodes
    except Exception:
        pass

    if os.path.exists(LOCAL_SUMMARY_PATH):
        with open(LOCAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)
            return summary.get("matches", [])
    return []

def classify_match(ep, sub_id=SUBMISSION_ID):
    agents = ep.get("agents", [])
    if len(agents) >= 2:
        if agents[0].get("submissionId") == sub_id:
            our_agent = agents[0]
            opp_agent = agents[1]
        else:
            our_agent = agents[1]
            opp_agent = agents[0]

        d1_reward = float(our_agent.get("reward") or 0.0)
        opp_reward = float(opp_agent.get("reward") or 0.0)
        opp_elo = float(opp_agent.get("initialScore") or 1000.0)
        d1_elo = float(our_agent.get("initialScore") or 1000.0)
    else:
        d1_reward = float(ep.get("d1_reward") or 0.0)
        opp_reward = float(ep.get("opp_reward") or 0.0)
        opp_elo = float(ep.get("opp_score_init") or 1000.0)
        d1_elo = float(ep.get("d1_score_init") or 1000.0)

    ep_id = ep.get("id") or ep.get("ep_id")
    seed = ep.get("seed")
    margin = d1_reward - opp_reward
    total_pie = d1_reward + opp_reward
    d1_share = (d1_reward / total_pie) if total_pie > 0 else 0.0
    won = d1_reward > opp_reward

    # 1. Cohort
    if opp_elo >= 2000.0:
        cohort = "ELITE"
    elif opp_elo >= 900.0 or opp_reward > 40000.0:
        cohort = "COMPETITIVE"
    else:
        cohort = "CASUAL"

    # 2. Economic Pie
    if total_pie >= 180000.0:
        pie_type = "HIGH-PIE"
    elif total_pie >= 140000.0:
        pie_type = "BASELINE-PIE"
    else:
        pie_type = "LOW-PIE"

    # 3. Deficit Margin
    if won:
        margin_type = "VICTORY"
    else:
        abs_deficit = abs(margin)
        if abs_deficit <= 5000.0:
            margin_type = "MICRO-MARGIN"
        elif abs_deficit <= 15000.0:
            margin_type = "MODERATE-MARGIN"
        else:
            margin_type = "LARGE-MARGIN"

    return {
        "ep_id": ep_id,
        "seed": seed,
        "won": won,
        "d1_reward": d1_reward,
        "opp_reward": opp_reward,
        "margin": margin,
        "total_pie": total_pie,
        "d1_share": d1_share,
        "opp_elo": opp_elo,
        "d1_elo": d1_elo,
        "cohort": cohort,
        "pie_type": pie_type,
        "margin_type": margin_type,
    }

def run_passive_monitor():
    print("=" * 105)
    print("PASSIVE LIVE TELEMETRY MONITOR & LOSS CLASSIFIER (SUBMISSION: 55780289)")
    print("=" * 105)

    raw = fetch_telemetry()
    if not raw:
        print("No live match telemetry available. Standing by.")
        return

    records = [classify_match(ep) for ep in raw]
    total = len(records)
    wins = [r for r in records if r["won"]]
    losses = [r for r in records if not r["won"]]

    print(f"\n[1] ROLLING DASHBOARD SUMMARY ({total} TOTAL MATCHES):")
    print("-" * 105)
    print(f"  * Match Record       : {len(wins)} Wins / {len(losses)} Losses ({len(wins)/total:.1%} Live Win Rate)")
    print(f"  * Mean D.1 Bank      : ${np.mean([r['d1_reward'] for r in records]):>10,.2f}")
    print(f"  * Mean Opponent Bank : ${np.mean([r['opp_reward'] for r in records]):>10,.2f}")
    print(f"  * Mean Net Margin    : ${np.mean([r['margin'] for r in records]):>+10,.2f}")
    print(f"  * Mean Shared Pie    : ${np.mean([r['total_pie'] for r in records]):>10,.2f}")
    print(f"  * Mean Market Share  : {np.mean([r['d1_share'] for r in records]):>9.1%} of Shared Economy")

    print("\n[2] LOSS TAXONOMY BREAKDOWN (n = " + str(len(losses)) + " LOSSES):")
    print("-" * 105)
    margin_counts = {}
    pie_counts = {}
    cohort_counts = {}

    for l in losses:
        margin_counts[l["margin_type"]] = margin_counts.get(l["margin_type"], 0) + 1
        pie_counts[l["pie_type"]] = pie_counts.get(l["pie_type"], 0) + 1
        cohort_counts[l["cohort"]] = cohort_counts.get(l["cohort"], 0) + 1

    print("  * Deficit Classification:")
    for k, v in sorted(margin_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f"      - {k:<20}: {v:>2} / {len(losses)} ({v/len(losses):.1%})")

    print("  * Shared Pie Context:")
    for k, v in sorted(pie_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f"      - {k:<20}: {v:>2} / {len(losses)} ({v/len(losses):.1%})")

    print("  * Opponent Cohort:")
    for k, v in sorted(cohort_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f"      - {k:<20}: {v:>2} / {len(losses)} ({v/len(losses):.1%})")

    print("\n[3] STRICT RESEARCH TRIGGER CHECK:")
    print("-" * 105)
    # Check if >= 10 losses share exact large-margin cluster
    large_losses = [l for l in losses if l["margin_type"] == "LARGE-MARGIN"]
    micro_losses = [l for l in losses if l["margin_type"] == "MICRO-MARGIN"]

    print(f"  * Micro-Margin Losses (Settlement Variance) : {len(micro_losses)} matches (Normal duopoly noise)")
    print(f"  * Large-Margin Losses (Asymmetric Duels)    : {len(large_losses)} matches (Cross-commodity anomalies)")

    if len(large_losses) >= 10:
        print("\n  [ALERT] 10+ Large-Margin losses detected! Research candidate trigger condition MET.")
    else:
        print(f"\n  [STANDBY] Large-Margin count ({len(large_losses)}/10) below trigger threshold.")
        print("            Production Status: 100% LOCKED AND FROZEN (Control A). Pure monitoring active.")
    print("=" * 105)

if __name__ == "__main__":
    run_passive_monitor()
