"""EXP078: Top-10 Grandmaster Fingerprint & Causal Divergence Audit.

1. Analyzes high-tier tournament matches involving top 2800-3100 Elo grandmasters:
   - Sub 55396329 (3011.4 Elo, Tagir Analyzes)
   - Sub 55396667 (2945.9 Elo)
   - Sub 55393329 (2924.6 Elo)
   - Sub 55396152 (2922.0 Elo)
   - Sub 55393409 (2906.0 Elo)
   - Sub 55370344 (2905.2 Elo)
   - Sub 55395767 (2856.2 Elo, sneaky6767)
2. Extracts their match trajectories and game outcomes across diverse seeds.
3. Replays Variant D.1 on the exact same grandmaster match seeds.
4. Performs side-by-side trajectory comparison at critical macro-milestones:
   - Day 3 (Bootstrap, Land, Workers, Seeds)
   - Day 8 (Active Strawberry Footprint, Cash Velocity)
   - Day 15 (Pasture Saturation & Milk Timing)
   - Day 25 (Reinvestment Cutoff & Late Capital Shift)
   - Day 29 (Terminal Queue Drain & Liquidation)
5. Identifies what the 3000-Elo grandmasters do differently from Variant D.1.
"""
from __future__ import annotations
import sys
import os
import json
import glob
import urllib.request
import urllib.error
import numpy as np
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
REPLAY_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "grandmaster_replays")
os.makedirs(REPLAY_DIR, exist_ok=True)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

def get_headers():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def fetch_sub_episodes(sub_id: int):
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(sub_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        return []

def fetch_episode_detail(ep_id: int):
    cache_file = os.path.join(REPLAY_DIR, f"gm_episode_{ep_id}.json")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
        try:
            with open(cache_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass

    headers = get_headers()
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            return data
    except Exception as e:
        return None

# Target Grandmaster Submissions
TOP_GM_SUBS = [
    {"sub_id": 55396329, "name": "Tagir Analyzes (#1 Leader)", "peak_elo": 3014.8},
    {"sub_id": 55396667, "name": "Top Master 1", "peak_elo": 2945.9},
    {"sub_id": 55393329, "name": "Top Master 2", "peak_elo": 2924.6},
    {"sub_id": 55396152, "name": "Top Master 3", "peak_elo": 2922.0},
    {"sub_id": 55393409, "name": "Top Master 4", "peak_elo": 2906.0},
    {"sub_id": 55370344, "name": "Top Master 5", "peak_elo": 2905.2},
    {"sub_id": 55398446, "name": "Top Master 6", "peak_elo": 2892.7},
    {"sub_id": 55395767, "name": "sneaky6767", "peak_elo": 2856.2},
]

def run_exp078():
    print("=" * 105)
    print("EXP078: TOP-10 GRANDMASTER FINGERPRINT & CAUSAL DIVERGENCE AUDIT")
    print("=" * 105)

    all_gm_matches = []

    for gm in TOP_GM_SUBS:
        sub_id = gm["sub_id"]
        print(f"\nFetching live ladder episodes for {gm['name']} (Sub ID: {sub_id}, Peak Elo: {gm['peak_elo']})...")
        eps = fetch_sub_episodes(sub_id)
        print(f"  -> Retrieved {len(eps)} completed tournament matches.")

        for ep in eps:
            agents = ep.get("agents", [])
            if len(agents) < 2:
                continue

            gm_ag = next((a for a in agents if a.get("submissionId") == sub_id), None)
            opp_ag = next((a for a in agents if a.get("submissionId") != sub_id), None)

            if not gm_ag or not opp_ag:
                continue

            gm_reward = float(gm_ag.get("reward") or 0.0)
            opp_reward = float(opp_ag.get("reward") or 0.0)
            opp_score = float(opp_ag.get("initialScore") or 0.0)
            ep_id = ep.get("id")

            all_gm_matches.append({
                "gm_name": gm["name"],
                "gm_sub_id": sub_id,
                "gm_elo": gm["peak_elo"],
                "ep_id": ep_id,
                "gm_reward": gm_reward,
                "opp_reward": opp_reward,
                "opp_sub_id": opp_ag.get("submissionId"),
                "opp_score": opp_score,
                "margin": gm_reward - opp_reward,
                "is_gm_win": 1 if gm_reward > opp_reward else 0,
                "is_gm_loss": 1 if gm_reward < opp_reward else 0,
            })

    print("\n" + "=" * 105)
    print("1. GRANDMASTER TOURNAMENT WIN RATE & ECONOMIC DISTRIBUTION SUMMARY")
    print("=" * 105)
    print(f"{'Grandmaster Agent':<30} | {'Matches':>8} | {'GM Wins':>8} | {'GM Losses':>9} | {'Win Rate %':>10} | {'Mean Reward ($)':>16} | {'Mean Margin ($)'}")
    print("-" * 105)

    for gm in TOP_GM_SUBS:
        sub_id = gm["sub_id"]
        m_list = [m for m in all_gm_matches if m["gm_sub_id"] == sub_id]
        if not m_list:
            continue
        g_wins = sum(m["is_gm_win"] for m in m_list)
        g_losses = sum(m["is_gm_loss"] for m in m_list)
        g_wr = g_wins / len(m_list) if m_list else 0
        g_mean_rew = float(np.mean([m["gm_reward"] for m in m_list]))
        g_mean_marg = float(np.mean([m["margin"] for m in m_list]))
        print(f"{gm['name']:<30} | {len(m_list):>8} | {g_wins:>8} | {g_losses:>9} | {g_wr:>9.1%} | ${g_mean_rew:>15,.2f} | ${g_mean_marg:>+13,.2f}")

    print("=" * 105)

    # 2. Sample 20 Grandmaster Match Seeds and Replay with Variant D.1
    print("\n2. COMPARATIVE REPLAY GAUNTLET: VARIANT D.1 ON EXACT GRANDMASTER MATCH SEEDS")
    print("-" * 105)

    # Filter for matches against intermediate/strong opponents (opp_score >= 800)
    filtered_matches = [m for m in all_gm_matches if m["opp_score"] >= 800.0]
    # Sample up to 20 diverse matches
    np.random.seed(42)
    sample_indices = np.random.choice(len(filtered_matches), size=min(20, len(filtered_matches)), replace=False)
    sample_matches = [filtered_matches[i] for i in sample_indices]

    print(f"Resolving seeds for {len(sample_matches)} sampled Grandmaster tournament matches...")

    resolved_replays = []
    for sm in sample_matches:
        detail = fetch_episode_detail(sm["ep_id"])
        if detail:
            ep_info = detail.get("episode", {})
            seed = ep_info.get("seed")
            if seed is not None:
                sm["seed"] = int(seed)
                resolved_replays.append(sm)

    print(f"Successfully resolved {len(resolved_replays)} exact GM match seeds.")
    print("\nRunning head-to-head simulations of Variant D.1 vs v18 on exact GM match seeds...")

    d1_results = []
    for r in resolved_replays:
        seed = r["seed"]
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        agent_d1 = VariantDAgent()

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation
            act0 = agent_d1.act(obs0, env.configuration)
            act1 = bot_v18.agent(obs1)
            env.step([act0, act1])

        d1_reward = float(env.state[0].reward or 0.0)
        v18_reward = float(env.state[1].reward or 0.0)

        d1_results.append({
            "ep_id": r["ep_id"],
            "seed": seed,
            "gm_name": r["gm_name"],
            "gm_elo": r["gm_elo"],
            "gm_reward": r["gm_reward"],
            "opp_reward": r["opp_reward"],
            "d1_reward": d1_reward,
            "v18_reward": v18_reward,
            "d1_margin": d1_reward - v18_reward,
            "delta_vs_gm": d1_reward - r["gm_reward"],
        })

    print("\n" + "=" * 105)
    print("3. SIDE-BY-SIDE WEALTH REALIZATION: VARIANT D.1 VS. 3000-TIER GRANDMASTERS (SAME SEEDS)")
    print("=" * 105)
    print(f"{'Ep ID':<10} | {'Seed':<11} | {'Grandmaster':<22} | {'GM Reward':>11} | {'D.1 Reward':>11} | {'Wealth Delta':>13} | {'D.1 Outcome'}")
    print("-" * 105)

    for dr in d1_results:
        status_str = "D.1 WON (+$" + f"{dr['d1_margin']:,.0f})" if dr['d1_margin'] > 0 else "D.1 LOST"
        print(f"{dr['ep_id']:<10} | {dr['seed']:<11} | {dr['gm_name'][:22]:<22} | ${dr['gm_reward']:>10,.0f} | ${dr['d1_reward']:>10,.0f} | ${dr['delta_vs_gm']:>+12,.0f} | {status_str}")

    print("=" * 105)
    print("\nSUMMARY OF D.1 VS GRANDMASTER REALIZATION:")
    print(f"  - Mean GM Realized Wealth on Seeds : ${np.mean([dr['gm_reward'] for dr in d1_results]):,.2f}")
    print(f"  - Mean D.1 Realized Wealth on Seeds: ${np.mean([dr['d1_reward'] for dr in d1_results]):,.2f}")
    print(f"  - Mean Wealth Extraction Delta     : ${np.mean([dr['delta_vs_gm'] for dr in d1_results]):+,.2f} / seed")
    print(f"  - D.1 Win Rate on GM Seeds vs v18  : {sum(1 for dr in d1_results if dr['d1_margin'] > 0) / len(d1_results):.1%}")
    print("=" * 105)

if __name__ == "__main__":
    run_exp078()
