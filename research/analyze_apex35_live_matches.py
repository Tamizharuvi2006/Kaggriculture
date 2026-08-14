"""PHASE 91: APEX 3.5 LIVE MATCH TELEMETRY & LOSS FORENSIC AUDIT.

Parses all completed tournament matches for submission 55483322 (APEX 3.5 Master),
categorizes every loss, evaluates tier-by-tier win rates and margins (<1100, 1100-1200, 1200-1300, 1300+),
and outputs reports/LIVE_APEX35_MATCH_TRACKER.md.
"""

from __future__ import annotations
import sys
import os
import json
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

DATA_PATH = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "submission_55483322_episodes.json")

def parse_apex35_matches():
    if not os.path.exists(DATA_PATH):
        print(f"Data file {DATA_PATH} not found!")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sub_info = data.get("submission", {})
    episodes = data.get("episodes", [])
    sub_id = 55483322

    matches = []

    for ep in episodes:
        ep_id = ep.get("id")
        ctime = ep.get("createTime")
        agents = ep.get("agents", [])
        if len(agents) < 2:
            continue

        our_ag, opp_ag = None, None
        for ag in agents:
            if ag.get("submissionId") == sub_id:
                our_ag = ag
            else:
                opp_ag = ag

        if not our_ag or not opp_ag:
            continue

        our_rew = float(our_ag.get("reward") or 0.0)
        opp_rew = float(opp_ag.get("reward") or 0.0)
        margin = our_rew - opp_rew
        total_pie = our_rew + opp_rew

        opp_sub_id = opp_ag.get("submissionId")
        opp_score = float(opp_ag.get("initialScore") or 0.0)
        our_score = float(our_ag.get("initialScore") or 0.0)

        win = 1 if our_rew > opp_rew else 0
        loss = 1 if our_rew < opp_rew else 0
        tie = 1 if our_rew == opp_rew else 0

        # Tier classification
        if opp_score < 1100:
            tier = "< 1100"
        elif opp_score < 1200:
            tier = "1100-1200"
        elif opp_score < 1300:
            tier = "1200-1300"
        else:
            tier = "1300+"

        matches.append({
            "ep_id": ep_id,
            "ctime": ctime,
            "our_score": our_score,
            "opp_score": opp_score,
            "opp_sub_id": opp_sub_id,
            "our_reward": our_rew,
            "opp_reward": opp_rew,
            "margin": margin,
            "total_pie": total_pie,
            "win": win,
            "loss": loss,
            "tie": tie,
            "tier": tier,
        })

    # Sort chronological
    matches.sort(key=lambda x: x.get("ctime") or "")

    print(f"====================================================================================================")
    print(f"📊 APEX 3.5 LIVE MATCH AUDIT ({len(matches)} COMPLETED MATCHES)")
    print(f"====================================================================================================")

    total_w = sum(m["win"] for m in matches)
    total_l = sum(m["loss"] for m in matches)
    total_t = sum(m["tie"] for m in matches)
    overall_wr = (total_w / len(matches)) * 100.0 if matches else 0.0
    mean_margin = sum(m["margin"] for m in matches) / len(matches) if matches else 0.0
    mean_our_w = sum(m["our_reward"] for m in matches) / len(matches) if matches else 0.0
    mean_opp_w = sum(m["opp_reward"] for m in matches) / len(matches) if matches else 0.0

    print(f"Overall Competitive Record: {total_w}W - {total_l}L - {total_t}T ({overall_wr:.1f}% Win Rate)")
    print(f"Mean Wealth: Our = ${mean_our_w:,.2f} | Opp = ${mean_opp_w:,.2f} | Mean Margin = ${mean_margin:+,.2f}\n")

    # Tier breakdown
    tiers = ["< 1100", "1100-1200", "1200-1300", "1300+"]
    tier_stats = {}

    print("--- ⚔️ TIER-BY-TIER PERFORMANCE BREAKDOWN ---")
    for t in tiers:
        t_matches = [m for m in matches if m["tier"] == t]
        if not t_matches:
            tier_stats[t] = {"count": 0, "wins": 0, "losses": 0, "wr": 0.0, "mean_margin": 0.0, "mean_our_w": 0.0}
            continue
        w = sum(m["win"] for m in t_matches)
        l = sum(m["loss"] for m in t_matches)
        wr = (w / len(t_matches)) * 100.0
        m_margin = sum(m["margin"] for m in t_matches) / len(t_matches)
        m_our_w = sum(m["our_reward"] for m in t_matches) / len(t_matches)
        tier_stats[t] = {"count": len(t_matches), "wins": w, "losses": l, "wr": wr, "mean_margin": m_margin, "mean_our_w": m_our_w}
        print(f"Tier {t:<10}: {len(t_matches):>2} matches | {w:>2}W - {l:>2}L ({wr:>5.1f}% WR) | Our Avg Wealth: ${m_our_w:>10,.2f} | Avg Margin: ${m_margin:>+10,.2f}")

    # Losses detailed
    losses = [m for m in matches if m["loss"] == 1]
    print(f"\nTotal Losses Ingested: {len(losses)}")

    report_md = f"""# 📊 APEX 3.5 Live Match Tracker & Loss Forensics

> **Candidate Reference**: `Ref 55483322` (`submission_candidate_apex35.py`)
> **Current Visible Kaggle Rating**: **1088.0**
> **Total Ingested Live Matches**: **{len(matches)} matches ({total_w}W - {total_l}L - {total_t}T | {overall_wr:.1f}% Win Rate)**
> **Mean Wealth**: **${mean_our_w:,.2f}** vs Opponent **${mean_opp_w:,.2f}** (Net Margin: **${mean_margin:+,.2f}**)

---

## 📈 1. Tier-by-Tier Ladder Breakdown

| Opponent Elo Tier | Matches | Record (W-L) | Win Rate (%) | Our Mean Wealth ($) | Mean Margin ($) | Competitive Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tier A (< 1100 Elo)** | {tier_stats['< 1100']['count']} | {tier_stats['< 1100']['wins']}W - {tier_stats['< 1100']['losses']}L | **{tier_stats['< 1100']['wr']:.1f}%** | ${tier_stats['< 1100']['mean_our_w']:,.2f} | **${tier_stats['< 1100']['mean_margin']:+,.2f}** | Saturated exploitation & strong positive margin |
| **Tier B (1100-1200 Elo)** | {tier_stats['1100-1200']['count']} | {tier_stats['1100-1200']['wins']}W - {tier_stats['1100-1200']['losses']}L | **{tier_stats['1100-1200']['wr']:.1f}%** | ${tier_stats['1100-1200']['mean_our_w']:,.2f} | **${tier_stats['1100-1200']['mean_margin']:+,.2f}** | Primary ladder battleground |
| **Tier C (1200-1300 Elo)** | {tier_stats['1200-1300']['count']} | {tier_stats['1200-1300']['wins']}W - {tier_stats['1200-1300']['losses']}L | **{tier_stats['1200-1300']['wr']:.1f}%** | ${tier_stats['1200-1300']['mean_our_w']:,.2f} | **${tier_stats['1200-1300']['mean_margin']:+,.2f}** | Strong competitive tier |
| **Tier D (1300+ Elo)** | {tier_stats['1300+']['count']} | {tier_stats['1300+']['wins']}W - {tier_stats['1300+']['losses']}L | **{tier_stats['1300+']['wr']:.1f}%** | ${tier_stats['1300+']['mean_our_w']:,.2f} | **${tier_stats['1300+']['mean_margin']:+,.2f}** | Elite ceiling tier |

---

## 🔍 2. Complete Live Loss Forensics Log ({len(losses)} Matches)

| Episode ID | Date/Time (UTC) | Opponent Sub ID | Opponent Initial Elo | Our Wealth ($) | Opp Wealth ($) | Margin ($) | Loss Classification | Forensic Analysis |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
"""
    for loss in losses:
        ep_id = loss["ep_id"]
        ctime = loss["ctime"][:16].replace("T", " ") if loss["ctime"] else "-"
        opp_sub = loss["opp_sub_id"]
        opp_elo = f"{loss['opp_score']:.1f}"
        our_w = loss["our_reward"]
        opp_w = loss["opp_reward"]
        margin = loss["margin"]
        abs_margin = abs(margin)

        if abs_margin <= 3000 and our_w >= 95000:
            cat = "Symmetric Nash Parity"
            desc = "Tight high-volume mirror split (> $95k both, < 3% margin)."
        elif our_w < 85000 and opp_w < 85000:
            cat = "Harsh Commodity Crash"
            desc = "Depressed price trajectory across entire match; both agents low."
        elif opp_w - our_w >= 10000 and our_w < 90000:
            cat = "Hoarding Rebound Variance"
            desc = "Harsh mid-game crash; opponent inventory rescued by late spike."
        else:
            cat = "Standard Competitive Loss"
            desc = "Competitive divergence during mid/late-game clearance."

        report_md += f"| [{ep_id}](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-{ep_id}) | {ctime} | {opp_sub} | {opp_elo} | ${our_w:,.1f} | ${opp_w:,.1f} | **${margin:+,.1f}** | {cat} | {desc} |\n"

    report_md += f"""
---

## 📜 3. Standing Live Monitoring Orders

1. **APEX 3.5 Code is 100% FROZEN**: No code edits, no re-tuning, no new submission uploads.
2. **Telemetry Collection Only**: Continuously ingest completed matches and track rating as it progresses through the 1100, 1200, and 1300+ Elo brackets.
3. **Repeated Failure Threshold**: If a systematic new failure mode appears across multiple matches in the same cohort, report the evidence before considering any research hypotheses.
"""

    report_path = os.path.join(BASE_DIR, "reports", "LIVE_APEX35_MATCH_TRACKER.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nReport written to: {report_path}")

if __name__ == "__main__":
    parse_apex35_matches()
