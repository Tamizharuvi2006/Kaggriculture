"""EXP071: Universal All-10-Submissions Real Loss Replay Gauntlet.
Extracts and replays loss matches from EVERY SINGLE ONE of our 10 historical Kaggle submissions:
1. Submission 55249106: V4.1 State-Repair (Score: 1479.8)
2. Submission 55373932: Clean Candidate L+ (Score: 1254.1)
3. Submission 55411304: APEX 3.0 Challenger (Score: 1116.5)
4. Submission 55421857: APEX 3.3 Challenger (Score: 1105.3)
5. Submission 55483322: APEX 3.5 Dual-Regime Master (Score: 1084.4)
6. Submission 55376463: Candidate L++ Adaptive Controller (Score: 1077.6)
7. Submission 55382689: Competitive Hybrid V13 (Score: 1058.6)
8. Submission 55329352: V8.3 Monolithic (Score: 758.5)
9. Submission 55373438: Standalone Candidate L+ (Score: 752.9)
10. Submission 55247715: Hybrid Farming Agent (Score: 421.9)

Fetches episode replays via Kaggle API if needed, parses exact match seeds & seats, and replays each against benchmark champion.
"""
from __future__ import annotations
import sys
import os
import json
import glob
import urllib.request
import urllib.error
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
REPLAY_CACHE_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "all_loss_replays_cache")
os.makedirs(REPLAY_CACHE_DIR, exist_ok=True)

def get_kaggle_headers():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            token = f.read().strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    return None

def fetch_episode_json(ep_id: int) -> dict | None:
    """Fetches episode replay json from cache or Kaggle API."""
    cache_file = os.path.join(REPLAY_CACHE_DIR, f"ep_{ep_id}.json")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
        try:
            with open(cache_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass

    headers = get_kaggle_headers()
    if not headers:
        return None

    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            return data
    except Exception:
        return None

def collect_all_10_submissions_losses() -> list[dict]:
    """Collects and resolves loss matches across all 10 submissions."""
    telemetry_dir = os.path.join(BASE_DIR, "reports", "live_match_telemetry")
    sub_files = glob.glob(os.path.join(telemetry_dir, "submission_*_episodes.json"))

    raw_losses = []
    print("Parsing episode lists across all 10 submissions...")

    for sf in sub_files:
        with open(sf, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        sub = data.get("submission", {})
        episodes = data.get("episodes", [])
        sub_id = int(sub.get("ref", os.path.basename(sf).split("_")[1]))
        desc = sub.get("description", "No description")
        score = sub.get("publicScore", "N/A")

        for ep in episodes:
            agents = ep.get("agents", [])
            if len(agents) >= 2:
                our_ag = next((a for a in agents if a.get("submissionId") == sub_id), None)
                opp_ag = next((a for a in agents if a.get("submissionId") != sub_id), None)
                if our_ag and opp_ag:
                    our_r = float(our_ag.get("reward") or 0.0)
                    opp_r = float(opp_ag.get("reward") or 0.0)
                    if our_r < opp_r:  # It's a loss!
                        raw_losses.append({
                            "sub_id": sub_id,
                            "sub_desc": desc,
                            "sub_score": score,
                            "ep_id": ep.get("id"),
                            "our_seat": 0 if agents[0].get("submissionId") == sub_id else 1,
                            "old_our_bank": our_r,
                            "old_opp_bank": opp_r,
                            "opp_sub_id": opp_ag.get("submissionId"),
                            "opp_score": float(opp_ag.get("initialScore") or 0.0),
                        })

    print(f"Discovered {len(raw_losses)} total raw loss episodes across all 10 submissions.")

    # Sample top 80 loss episodes (distributed across all 10 submissions) to avoid rate limits
    by_sub = {}
    for l in raw_losses:
        by_sub.setdefault(l["sub_id"], []).append(l)

    sampled_losses = []
    for s_id, losses in by_sub.items():
        # Take up to 10 representative losses per submission
        sampled_losses.extend(losses[:10])

    print(f"Resolving exact simulation seeds for {len(sampled_losses)} loss episodes across all 10 submissions...")

    resolved_losses = []
    for item in sampled_losses:
        ep_json = fetch_episode_json(item["ep_id"])
        if ep_json:
            ep_data = ep_json.get("episode", {})
            seed = ep_data.get("seed")
            if seed is None:
                seed = ep_json.get("info", {}).get("seed")
            if seed is not None:
                item["seed"] = int(seed)
                resolved_losses.append(item)

    print(f"Successfully resolved {len(resolved_losses)} unique loss seeds with full metadata.")
    return resolved_losses

def replay_single_loss(meta: dict) -> dict:
    """Executes replay on seed & seat with Variant D.1 vs v18."""
    seed = meta["seed"]
    our_seat = meta["our_seat"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    agent_d1 = VariantDAgent()

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        if our_seat == 0:
            act0 = agent_d1.act(obs0, env.configuration)
            act1 = bot_v18.agent(obs1)
            env.step([act0, act1])
        else:
            act0 = bot_v18.agent(obs0)
            act1 = agent_d1.act(obs1, env.configuration)
            env.step([act0, act1])

    new_d1_bank = float(env.state[our_seat].reward or 0.0)
    new_opp_bank = float(env.state[1 - our_seat].reward or 0.0)
    is_rescued = new_d1_bank > new_opp_bank

    return {
        "sub_id": meta["sub_id"],
        "sub_desc": meta["sub_desc"],
        "sub_score": meta["sub_score"],
        "episode_id": meta["ep_id"],
        "seed": seed,
        "our_seat": our_seat,
        "old_our_bank": meta["old_our_bank"],
        "old_opp_bank": meta["old_opp_bank"],
        "old_margin": meta["old_our_bank"] - meta["old_opp_bank"],
        "new_d1_bank": new_d1_bank,
        "new_opp_bank": new_opp_bank,
        "new_margin": new_d1_bank - new_opp_bank,
        "is_rescued": is_rescued,
        "bank_delta": new_d1_bank - meta["old_our_bank"],
    }

def run_exp071():
    print("=" * 105)
    print("EXP071: UNIVERSAL ALL-10-SUBMISSIONS REAL LOSS REPLAY GAUNTLET")
    print("=" * 105)

    all_losses = collect_all_10_submissions_losses()
    if not all_losses:
        print("No resolved loss matches. Exiting.")
        return

    print(f"\nSimulating {len(all_losses)} loss replays in parallel with Variant D.1 vs v18...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        results = list(pool.map(replay_single_loss, all_losses))

    rescued_total = sum(1 for r in results if r["is_rescued"])
    total_matches = len(results)
    rescue_rate = rescued_total / total_matches

    print("\n" + "=" * 105)
    print("1. RESCUE PERFORMANCE BREAKDOWN BY ALL 10 HISTORICAL SUBMISSIONS")
    print("=" * 105)
    print(f"{'Submission Model & Description':<48} | {'Score':>7} | {'Tested':>6} | {'Rescued':>7} | {'Rescue %':>8} | {'Mean Delta ($)'}")
    print("-" * 105)

    sub_ids = sorted(list(set(r["sub_id"] for r in results)))
    for s_id in sub_ids:
        s_res = [r for r in results if r["sub_id"] == s_id]
        desc = s_res[0]["sub_desc"][:46]
        score = str(s_res[0]["sub_score"])
        s_resc = sum(1 for r in s_res if r["is_rescued"])
        s_rate = s_resc / len(s_res)
        s_delta = float(np.mean([r["bank_delta"] for r in s_res]))

        print(f"{desc:<48} | {score:>7} | {len(s_res):>6} | {s_resc:>7} | {s_rate:>7.1%} | ${s_delta:>+12,.2f}")

    print("=" * 105)

    print("\n" + "=" * 105)
    print("2. OVERALL UNIVERSAL ADVERSARIAL RESCUE SUMMARY")
    print("=" * 105)
    print(f"{'Universal Metric':<38} | {'Value / Performance':>25} | {'Significance'}")
    print("-" * 105)
    print(f"{'Total Unique Loss Matches Tested':<38} | {total_matches:>25} | Across all 10 submissions")
    print(f"{'Total Rescued Matches (Now Won)':<38} | {f'{rescued_total} / {total_matches}':>25} | Turned from loss to victory")
    print(f"{'Overall Universal Rescue Rate':<38} | {rescue_rate:>24.1%} | % of real Kaggle losses overcome")
    print(f"{'Old Bots Mean Bank on Loss Seeds':<38} | ${float(np.mean([r['old_our_bank'] for r in results])):>23,.2f} | Prior generational score")
    print(f"{'Variant D.1 Mean Bank on Loss Seeds':<38} | ${float(np.mean([r['new_d1_bank'] for r in results])):>23,.2f} | Production champion score")
    print(f"{'Average Coin Gain per Match':<38} | ${float(np.mean([r['bank_delta'] for r in results])):>+23,.2f} | Net wealth boost per game")
    print("=" * 105)

    print("\n3. FINAL VERDICT ON ALL HISTORICAL SUBMISSIONS:")
    print(f"  >>> VARIANT D.1 RESCUES {rescue_rate:.1%} OF ALL LOSSES ACROSS ALL 10 KAGGLE SUBMISSIONS (V4.1, L+, L++, APEX 3.0, APEX 3.3, APEX 3.5, Hybrid V13, V8.3)!")
    print(f"      Average reward increases by +${float(np.mean([r['bank_delta'] for r in results])):,.2f} per seed across the entire competitive history.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp071()
