#!/usr/bin/env python3
"""Live Telemetry & Loss Sentry Dashboard for Kaggriculture.

Monitors live Kaggle submissions, tracks Elo progression, match records,
identifies opponent archetypes, and automatically flags and downloads
low-Elo losses for instant forensic analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TOKEN_PATH = Path(r"C:\Users\aruvi\.kaggle\access_token")
OUTPUT_DIR = Path(r"D:\kaggriculture\reports\live_match_telemetry")
LOSS_REGISTRY_PATH = OUTPUT_DIR / "loss_registry.json"

DEFAULT_TRACKED_SUBS = [
    55935415,  # EXP212 Responder V6 (Staged Live Challenger ⚔️)
    55934470,  # EXP208 Clean-Room Production Build (Active Benchmark 🌾)
    55924297,  # EXP208 Champion Challenger (Previous)
    55924286,  # EXP208 Champion Policy (Previous)
]


def load_token() -> str:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"Kaggle access token not found at {TOKEN_PATH}")
    return TOKEN_PATH.read_text(encoding="utf-8").strip()


def api_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = load_token()
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "KaggricultureLiveDashboard/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_episode_replay(episode_id: int) -> Optional[Dict[str, Any]]:
    # Replays are stored directly on GCS
    gcs_url = f"https://storage.googleapis.com/kaggle-episodes/{episode_id}.json"
    req = urllib.request.Request(gcs_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def fetch_submission_episodes(submission_id: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        data = api_request("ListEpisodes", {"submissionId": submission_id})
        episodes = data.get("episodes", [])
        subs = data.get("submissions", [])
        sub_meta = next((s for s in subs if s.get("id") == submission_id), {})
        return episodes, sub_meta
    except Exception as e:
        print(f"[!] Error fetching episodes for submission {submission_id}: {e}")
        return [], {}


def analyze_matches(
    submission_id: int, episodes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    completed = [
        ep for ep in episodes
        if ep.get("state") == "COMPLETED" and ep.get("type") != "EPISODE_TYPE_VALIDATION"
    ]
    validation = [
        ep for ep in episodes
        if ep.get("type") == "EPISODE_TYPE_VALIDATION"
    ]

    wins = 0
    losses = 0
    ties = 0
    hero_scores = []
    opp_scores = []
    matches = []
    low_elo_losses = []

    current_elo = 600.0
    initial_elo = 600.0

    for ep in completed:
        ep_id = ep.get("id")
        agents = ep.get("agents", [])
        if len(agents) < 2:
            continue

        hero_idx = next(
            (i for i, a in enumerate(agents) if a.get("submissionId") == submission_id),
            None,
        )
        if hero_idx is None:
            continue
        opp_idx = 1 - hero_idx

        hero_a = agents[hero_idx]
        opp_a = agents[opp_idx]

        h_reward = hero_a.get("reward")
        o_reward = opp_a.get("reward")
        h_score = hero_a.get("updatedScore") or hero_a.get("initialScore")
        o_score = opp_a.get("initialScore") or opp_a.get("updatedScore")

        if h_score is not None:
            current_elo = float(h_score)
        if initial_elo == 600.0 and hero_a.get("initialScore"):
            initial_elo = float(hero_a.get("initialScore"))

        if h_reward is None or o_reward is None:
            continue

        h_reward = float(h_reward)
        o_reward = float(o_reward)
        hero_scores.append(h_reward)
        opp_scores.append(o_reward)

        delta = h_reward - o_reward
        opp_elo = float(o_score) if o_score is not None else 600.0

        res_str = "TIE"
        if delta > 0:
            res_str = "WIN"
            wins += 1
        elif delta < 0:
            res_str = "LOSS"
            losses += 1
        else:
            ties += 1

        match_info = {
            "episode_id": ep_id,
            "result": res_str,
            "hero_reward": h_reward,
            "opp_reward": o_reward,
            "delta": delta,
            "opp_elo": opp_elo,
            "hero_seat": hero_idx,
            "date": ep.get("createTime", "")[:19].replace("T", " "),
        }
        matches.append(match_info)

        # Flag Low-Elo loss (Opponent Elo < 1100)
        if res_str == "LOSS" and opp_elo < 1100:
            low_elo_losses.append(match_info)

    tot = wins + losses + ties
    win_rate = (wins + 0.5 * ties) / tot * 100.0 if tot > 0 else 0.0

    avg_hero = sum(hero_scores) / len(hero_scores) if hero_scores else 0.0
    avg_opp = sum(opp_scores) / len(opp_scores) if opp_scores else 0.0
    avg_margin = avg_hero - avg_opp

    sorted_by_delta = sorted(matches, key=lambda m: m["delta"])
    biggest_loss = sorted_by_delta[0] if sorted_by_delta and sorted_by_delta[0]["delta"] < 0 else None
    biggest_win = sorted_by_delta[-1] if sorted_by_delta and sorted_by_delta[-1]["delta"] > 0 else None

    return {
        "submission_id": submission_id,
        "total_episodes": len(episodes),
        "validation_count": len(validation),
        "matches_count": tot,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": win_rate,
        "current_elo": current_elo,
        "initial_elo": initial_elo,
        "avg_hero": avg_hero,
        "avg_opp": avg_opp,
        "avg_margin": avg_margin,
        "biggest_win": biggest_win,
        "biggest_loss": biggest_loss,
        "low_elo_losses": low_elo_losses,
        "recent_matches": matches[-8:],
        "matches": matches,
    }


def auto_save_and_download_losses(low_losses: List[Dict[str, Any]]) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = {}
    if LOSS_REGISTRY_PATH.exists():
        try:
            registry = json.loads(LOSS_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            registry = {}

    downloaded = 0
    for loss in low_losses:
        eid = str(loss["episode_id"])
        if eid not in registry:
            registry[eid] = {
                **loss,
                "recorded_at": datetime.now().isoformat(),
            }
        # Download full replay for offline forensics if not present
        replay_file = OUTPUT_DIR / f"episode-{eid}-replay.json"
        if not replay_file.exists():
            rep_data = get_episode_replay(loss["episode_id"])
            if rep_data:
                replay_file.write_text(json.dumps(rep_data, indent=2), encoding="utf-8")
                downloaded += 1

    LOSS_REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return downloaded


def render_dashboard(active_sid: int, all_analyses: List[Dict[str, Any]]):
    active = next((a for a in all_analyses if a["submission_id"] == active_sid), None)
    os.system("cls" if os.name == "nt" else "clear")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 95)
    print(f" 🌾 KAGGRICULTURE LIVE LADDER TELEMETRY & FORENSIC SENTRY 🌾      [{now_str}]")
    print("=" * 95)

    if not active:
        print(f"No telemetry found for active submission {active_sid}")
        return

    # Header Card for Active Submission
    elo_delta = active["current_elo"] - active["initial_elo"]
    elo_delta_str = f"{elo_delta:+.1f}" if elo_delta != 0 else "+0.0"
    print(f" Active Challenger : #{active['submission_id']} (EXP208 Clean-Room Production Build)")
    print(f" Ladder Standing   : Elo {active['current_elo']:.1f} ({elo_delta_str}) | Games: {active['matches_count']} ({active['wins']}W / {active['losses']}L / {active['ties']}T)")
    print(f" Win Rate & Margin : {active['win_rate']:.1f}% Win Rate | Mean Margin: {active['avg_margin']:+,.0f} (Hero: ${active['avg_hero']:,.0f} vs Opp: ${active['avg_opp']:,.0f})")

    if active["biggest_win"]:
        bw = active["biggest_win"]
        print(f" 🏆 Biggest Win    : Ep {bw['episode_id']} vs Opp Elo {bw['opp_elo']:.0f} (${bw['hero_reward']:,.0f} vs ${bw['opp_reward']:,.0f}, Margin: {bw['delta']:+,.0f})")
    if active["biggest_loss"]:
        bl = active["biggest_loss"]
        print(f" 📉 Biggest Loss   : Ep {bl['episode_id']} vs Opp Elo {bl['opp_elo']:.0f} (${bl['hero_reward']:,.0f} vs ${bl['opp_reward']:,.0f}, Margin: {bl['delta']:+,.0f})")

    # Low-Elo Alert Section
    low_losses = active.get("low_elo_losses", [])
    if low_losses:
        print("\n" + "!" * 95)
        print(f" 🚨 SENTRY ALERT: {len(low_losses)} LOW-ELO LOSS(ES) DETECTED ON LIVE LADDER! 🚨")
        print("!" * 95)
        for l in low_losses:
            print(f"  • Episode {l['episode_id']} (Seat {l['hero_seat']}) vs Opponent Elo {l['opp_elo']:.0f}:")
            print(f"    Our Wealth: ${l['hero_reward']:,.0f} | Opp Wealth: ${l['opp_reward']:,.0f} | Deficit: {l['delta']:+,.0f}")
            print(f"    Replay auto-cataloged to: reports/live_match_telemetry/episode-{l['episode_id']}-replay.json")
    else:
        print("\n ✅ SENTRY STATUS: 0 Low-Elo (<1100) losses detected on the current active submission.")

    # Recent Matches Table
    print("\n" + "-" * 95)
    print(f" {'RECENT LIVE MATCHES (LAST 8)':^93} ")
    print("-" * 95)
    print(f" {'Episode ID':^12} | {'Result':^6} | {'Hero Wealth':^15} | {'Opp Wealth':^15} | {'Margin':^14} | {'Opp Elo':^9} | {'Seat':^4}")
    print("-" * 95)
    if not active["recent_matches"]:
        print(f" {'No completed ladder matches recorded yet (provisional validation complete)':^93}")
    else:
        for m in reversed(active["recent_matches"]):
            res_tag = "✅ WIN " if m["result"] == "WIN" else ("❌ LOSS" if m["result"] == "LOSS" else "⚖️ TIE ")
            print(f" {m['episode_id']:^12} | {res_tag:^6} | ${m['hero_reward']:13,.0f} | ${m['opp_reward']:13,.0f} | {m['delta']:+12,.0f} | {m['opp_elo']:^9.0f} | {m['hero_seat']:^4}")
    print("-" * 95)

    # Historical Submissions Comparison Table
    print(f"\n {'HISTORICAL SUBMISSIONS TELEMETRY':^93} ")
    print("-" * 95)
    print(f" {'Sub ID':^10} | {'Status':^8} | {'Elo':^7} | {'Matches':^7} | {'Win %':^7} | {'Hero Mean':^13} | {'Opp Mean':^13} | {'Low Losses':^10}")
    print("-" * 95)
    for a in all_analyses:
        mark = "👉" if a["submission_id"] == active_sid else "  "
        st = "ACTIVE" if a["submission_id"] == active_sid else "LOCKED"
        print(f"{mark}{a['submission_id']:^8} | {st:^8} | {a['current_elo']:^7.1f} | {a['matches_count']:^7} | {a['win_rate']:^6.1f}% | ${a['avg_hero']:11,.0f} | ${a['avg_opp']:11,.0f} | {len(a['low_elo_losses']):^10}")
    print("=" * 95)


def main():
    parser = argparse.ArgumentParser(description="Kaggriculture Live Submission Telemetry & Loss Sentry")
    parser.add_argument("--sub", type=int, default=55934470, help="Primary submission ID to monitor (default: 55934470)")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring loop (polls every N seconds)")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds for --watch (default: 60)")
    args = parser.parse_args()

    active_sid = args.sub
    all_sids = [active_sid] + [s for s in DEFAULT_TRACKED_SUBS if s != active_sid]

    try:
        while True:
            analyses = []
            for sid in all_sids:
                eps, meta = fetch_submission_episodes(sid)
                ana = analyze_matches(sid, eps)
                analyses.append(ana)
                if sid == active_sid and ana["low_elo_losses"]:
                    auto_save_and_download_losses(ana["low_elo_losses"])

            render_dashboard(active_sid, analyses)

            if not args.watch:
                break

            print(f"\n[Watch Mode] Next refresh in {args.interval} seconds... (Press Ctrl+C to exit)")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nLive Dashboard stopped.")


if __name__ == "__main__":
    main()
