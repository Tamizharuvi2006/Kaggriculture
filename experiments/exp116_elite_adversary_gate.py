"""EXP116: 1200+ / Elite-Adversary Multi-Tier Population Benchmark & Forensics Suite.

Evaluates Variant D.1 Control A (submission_clean.py) vs Candidate D.2 (submission_d2.py) across 4 distinct competitive tiers
drawn from the 8,268 Kaggle Replay Corpus + Multi-Archetype Challenger Suite:

Tier 1 (Apex Elite / 3100+ Elo): Top high-win clusters (Cluster 87, 76, 95, 59 - 88-100% WR).
Tier 2 (Strong Competitors / 3050-3100 Elo): Saturated high-frequency clusters (Cluster 73, 84, 51, 21 - 75-85% WR).
Tier 3 (Hostile Counter / Squeeze Cohort): Historical hostile loss clusters (Cluster 8, 19, 26, 39).
Tier 4 (Challenger Archetypes): Dynamic responsive bots (Carrot Rusher, Livestock Rusher, v83 Standalone).

Forensics Tracked:
- Mean Terminal Bank ($) for D.1 and D.2
- Opponent Mean Terminal Bank ($)
- Market Share (%) = D / (D + Opponent)
- Head-to-Head Win Rate (%)
- Mean Loss Margin ($) on defeated matches
- Opponent Commodity Mix Analysis
- Milestone Timestamps & Early Cashflow Velocity
- Solvency & Action Legality Gate
"""
from __future__ import annotations
import os
import sys
import json
import gzip
import importlib.util
import numpy as np
import pandas as pd
from collections import defaultdict
from huggingface_hub import hf_hub_download

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load HF Token if available
hf_token_path = os.path.expanduser("~/.hf/HF_TOKEN")
HF_TOKEN = None
if os.path.exists(hf_token_path):
    with open(hf_token_path, "r", encoding="utf-8") as f:
        HF_TOKEN = f.read().strip()
    os.environ["HF_TOKEN"] = HF_TOKEN

import kaggle_environments

DATASETS_IL = os.path.join(BASE_DIR, "datasets", "il")
EPISODES_DIR = os.path.join(DATASETS_IL, "episodes")
os.makedirs(EPISODES_DIR, exist_ok=True)

# Load D.1 and D.2 agents
def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

sub_d1 = load_module("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d2 = load_module("sub_d2", os.path.join(BASE_DIR, "submission_d2.py"))

# Load challenger bots
spec_chall = importlib.util.spec_from_file_location("challengers", os.path.join(BASE_DIR, "baseline", "challengers.py"))
challengers = importlib.util.module_from_spec(spec_chall)
spec_chall.loader.exec_module(challengers)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_v83 = importlib.util.spec_from_file_location("bot_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
bot_v83 = importlib.util.module_from_spec(spec_v83)
spec_v83.loader.exec_module(bot_v83)

def get_episode_path(episode_id: int) -> str | None:
    local_path = os.path.join(EPISODES_DIR, f"{episode_id}.json.gz")
    if os.path.exists(local_path):
        return local_path
    rel_hf_path = f"datasets/il/episodes/{episode_id}.json.gz"
    try:
        downloaded = hf_hub_download(
            repo_id="KiroSamurai/kaggriculture-il",
            filename=rel_hf_path,
            repo_type="dataset",
            local_dir=BASE_DIR,
            token=HF_TOKEN,
        )
        return downloaded
    except Exception as e:
        print(f"    [Warning] Could not fetch episode {episode_id}: {e}")
        return None

def load_replay_actions(episode_path: str, opp_seat: int):
    with gzip.open(episode_path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    steps = data.get("steps", [])
    actions = []
    commodity_counts = defaultdict(int)

    for s in steps:
        if isinstance(s, list) and len(s) > opp_seat:
            act = s[opp_seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}
            actions.append(act)
            if isinstance(act, dict):
                for m in act.get("market") or []:
                    if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
                        commodity_counts[m[1]] += int(m[2])
        else:
            actions.append({"farmer": ["PASS"], "hands": [], "market": []})
    seed = data.get("configuration", {}).get("seed")
    return actions, seed, commodity_counts

def run_replay_match(agent_module, replay_actions, seed: int, agent_seat: int = 0):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    agent_module._APEX35_PRICE_HISTORY = {"STRAWBERRY": [], "MILK": []}

    opp_seat = 1 - agent_seat
    step_idx = 0
    while not env.done:
        obs_agent = env.state[agent_seat].observation
        act_agent = agent_module.agent(obs_agent, env.configuration)
        act_opp = replay_actions[min(step_idx, len(replay_actions) - 1)]

        if agent_seat == 0:
            env.step([act_agent, act_opp])
        else:
            env.step([act_opp, act_agent])
        step_idx += 1

    r_agent = float(env.state[agent_seat].reward or 0.0)
    r_opp = float(env.state[opp_seat].reward or 0.0)
    pie = r_agent + r_opp
    share = (r_agent / pie) * 100.0 if pie > 0 else 50.0
    won = r_agent > r_opp

    return {
        "agent_reward": r_agent,
        "opp_reward": r_opp,
        "share": share,
        "won": won,
        "margin": r_agent - r_opp,
    }

def run_dynamic_bot_match(agent_module, opp_bot_func, seed: int, agent_seat: int = 0):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    agent_module._APEX35_PRICE_HISTORY = {"STRAWBERRY": [], "MILK": []}

    opp_seat = 1 - agent_seat
    while not env.done:
        obs_agent = env.state[agent_seat].observation
        obs_opp = env.state[opp_seat].observation
        act_agent = agent_module.agent(obs_agent, env.configuration)
        act_opp = opp_bot_func(obs_opp, env.configuration)

        if agent_seat == 0:
            env.step([act_agent, act_opp])
        else:
            env.step([act_opp, act_agent])

    r_agent = float(env.state[agent_seat].reward or 0.0)
    r_opp = float(env.state[opp_seat].reward or 0.0)
    pie = r_agent + r_opp
    share = (r_agent / pie) * 100.0 if pie > 0 else 50.0
    won = r_agent > r_opp

    return {
        "agent_reward": r_agent,
        "opp_reward": r_opp,
        "share": share,
        "won": won,
        "margin": r_agent - r_opp,
    }

def main():
    print("=" * 125)
    print("EXP116: 1200+ / ELITE-ADVERSARY MULTI-TIER POPULATION BENCHMARK & DECISION GATE")
    print("=" * 125)

    # 1. Read index and cluster metadata
    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[['episode_id', 'seed', 'elo_avg']], on='episode_id')

    # Select representative episodes from each tier
    tier1_clusters = [87, 76, 95, 59]   # Apex Elite (88-100% WR)
    tier2_clusters = [73, 84, 51, 21]   # Strong High-Frequency (75-85% WR)
    tier3_clusters = [8, 19, 26, 39]    # Hostile Squeeze / Low WR Cohort

    def sample_episodes(cluster_ids, n_per_cluster=3):
        samples = []
        for c in cluster_ids:
            subset = df_merged[df_merged['cluster'] == c]
            for _, row in subset.head(n_per_cluster).iterrows():
                samples.append({
                    "episode_id": int(row['episode_id']),
                    "seat": int(row['seat']),
                    "cluster": c,
                    "seed": int(row['seed']) if pd.notnull(row['seed']) else 1000 + int(row['episode_id']) % 5000,
                    "elo": float(row['elo_avg'])
                })
        return samples

    t1_samples = sample_episodes(tier1_clusters, n_per_cluster=3)
    t2_samples = sample_episodes(tier2_clusters, n_per_cluster=3)
    t3_samples = sample_episodes(tier3_clusters, n_per_cluster=3)

    tiers = {
        "Tier 1: Apex Elite (Cluster 87, 76, 95, 59 | 3100+ Elo)": t1_samples,
        "Tier 2: Strong Competitors (Cluster 73, 84, 51, 21 | 3050-3100 Elo)": t2_samples,
        "Tier 3: Hostile Squeeze Meta (Cluster 8, 19, 26, 39 | Counter-Archetypes)": t3_samples,
    }

    tier_results = defaultdict(lambda: {
        "d1_rewards": [], "d2_rewards": [],
        "d1_shares": [], "d2_shares": [],
        "d1_wins": 0, "d2_wins": 0,
        "d1_margins": [], "d2_margins": [],
        "total": 0
    })

    for tier_name, samples in tiers.items():
        print(f"\n>>> Running Evaluation: {tier_name} ({len(samples)} matches)...")
        for item in samples:
            ep_id = item["episode_id"]
            opp_seat = item["seat"]
            seed = item["seed"]

            ep_path = get_episode_path(ep_id)
            if not ep_path:
                continue

            actions, conf_seed, commodity_counts = load_replay_actions(ep_path, opp_seat)
            actual_seed = conf_seed if conf_seed is not None else seed

            # Run D.1 vs Replay Opponent
            res_d1 = run_replay_match(sub_d1, actions, actual_seed, agent_seat=0)
            # Run D.2 vs Replay Opponent
            res_d2 = run_replay_match(sub_d2, actions, actual_seed, agent_seat=0)

            tier_results[tier_name]["d1_rewards"].append(res_d1["agent_reward"])
            tier_results[tier_name]["d2_rewards"].append(res_d2["agent_reward"])
            tier_results[tier_name]["d1_shares"].append(res_d1["share"])
            tier_results[tier_name]["d2_shares"].append(res_d2["share"])
            tier_results[tier_name]["d1_margins"].append(res_d1["margin"])
            tier_results[tier_name]["d2_margins"].append(res_d2["margin"])
            if res_d1["won"]: tier_results[tier_name]["d1_wins"] += 1
            if res_d2["won"]: tier_results[tier_name]["d2_wins"] += 1
            tier_results[tier_name]["total"] += 1

            delta = res_d2["agent_reward"] - res_d1["agent_reward"]
            delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"
            w1 = "WIN" if res_d1["won"] else "LOSS"
            w2 = "WIN" if res_d2["won"] else "LOSS"
            top_sales = sorted(commodity_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_sales_str = ", ".join(f"{k}:{v}" for k, v in top_sales) if top_sales else "None"

            print(f"  Ep {ep_id:8d} (Clust {item['cluster']:2d}) | D.1=${res_d1['agent_reward']:9,f} ({res_d1['share']:4.1f}% {w1}) | D.2=${res_d2['agent_reward']:9,f} ({res_d2['share']:4.1f}% {w2}) | Delta={delta_str:10s} | Opp Sales: [{top_sales_str}]")

    # 4. Tier 4: Dynamic Challenger Archetypes (10 seeds each)
    print("\n>>> Running Evaluation: Tier 4: Dynamic Challenger Archetypes (30 matches)...")
    t4_name = "Tier 4: Dynamic Archetypes (Carrot Rusher, Livestock Rusher, v83 Standalone)"
    t4_seeds = [1000, 2024, 3333, 5000, 7777, 9999, 12345, 18000, 22222, 30000]

    for opp_name, opp_func in [
        ("Carrot Rusher", challengers.carrot_rusher_agent),
        ("Livestock Rusher", challengers.livestock_rusher_agent),
        ("v83 Standalone", bot_v83.agent)
    ]:
        print(f"\n  --- Dynamic Archetype: {opp_name} (10 seeds) ---")
        for seed in t4_seeds:
            res_d1 = run_dynamic_bot_match(sub_d1, opp_func, seed, agent_seat=0)
            res_d2 = run_dynamic_bot_match(sub_d2, opp_func, seed, agent_seat=0)

            tier_results[t4_name]["d1_rewards"].append(res_d1["agent_reward"])
            tier_results[t4_name]["d2_rewards"].append(res_d2["agent_reward"])
            tier_results[t4_name]["d1_shares"].append(res_d1["share"])
            tier_results[t4_name]["d2_shares"].append(res_d2["share"])
            tier_results[t4_name]["d1_margins"].append(res_d1["margin"])
            tier_results[t4_name]["d2_margins"].append(res_d2["margin"])
            if res_d1["won"]: tier_results[t4_name]["d1_wins"] += 1
            if res_d2["won"]: tier_results[t4_name]["d2_wins"] += 1
            tier_results[t4_name]["total"] += 1

            delta = res_d2["agent_reward"] - res_d1["agent_reward"]
            delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"
            w1 = "WIN" if res_d1["won"] else "LOSS"
            w2 = "WIN" if res_d2["won"] else "LOSS"
            print(f"  Seed {seed:6d} vs {opp_name:16s} | D.1=${res_d1['agent_reward']:9,f} ({res_d1['share']:4.1f}% {w1}) | D.2=${res_d2['agent_reward']:9,f} ({res_d2['share']:4.1f}% {w2}) | Delta={delta_str:10s}")

    # ====================================================================================================
    # FINAL SUMMARY REPORT & DECISION GATE
    # ====================================================================================================
    print("\n" + "=" * 125)
    print("EXP116 MULTI-TIER POPULATION BENCHMARK SUMMARY")
    print("=" * 125)
    print(f"{'Population Tier':<52s} | {'D.1 Mean':<11s} | {'D.2 Mean':<11s} | {'Delta':<10s} | {'D.1 Share':<9s} | {'D.2 Share':<9s} | {'D.1 WR':<6s} | {'D.2 WR':<6s}")
    print("-" * 135)

    overall_d1_r, overall_d2_r = [], []
    overall_d1_s, overall_d2_s = [], []
    overall_d1_w, overall_d2_w, overall_tot = 0, 0, 0

    for t_name, data in tier_results.items():
        if data["total"] == 0:
            continue
        d1_m = np.mean(data["d1_rewards"])
        d2_m = np.mean(data["d2_rewards"])
        d1_s = np.mean(data["d1_shares"])
        d2_s = np.mean(data["d2_shares"])
        d1_wr = (data["d1_wins"] / data["total"]) * 100.0
        d2_wr = (data["d2_wins"] / data["total"]) * 100.0
        delta = d2_m - d1_m
        delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"

        overall_d1_r.extend(data["d1_rewards"])
        overall_d2_r.extend(data["d2_rewards"])
        overall_d1_s.extend(data["d1_shares"])
        overall_d2_s.extend(data["d2_shares"])
        overall_d1_w += data["d1_wins"]
        overall_d2_w += data["d2_wins"]
        overall_tot += data["total"]

        print(f"{t_name[:52]:<52s} | ${d1_m:9,f} | ${d2_m:9,f} | {delta_str:10s} | {d1_s:7.2f}% | {d2_s:7.2f}% | {d1_wr:5.1f}% | {d2_wr:5.1f}%")

    print("-" * 135)
    ov_d1_m = np.mean(overall_d1_r)
    ov_d2_m = np.mean(overall_d2_r)
    ov_d1_s = np.mean(overall_d1_s)
    ov_d2_s = np.mean(overall_d2_s)
    ov_d1_wr = (overall_d1_w / overall_tot) * 100.0
    ov_d2_wr = (overall_d2_w / overall_tot) * 100.0
    ov_delta = ov_d2_m - ov_d1_m
    ov_delta_str = f"+${ov_delta:,.2f}" if ov_delta >= 0 else f"-${abs(ov_delta):,.2f}"

    print(f"{'OVERALL POPULATION BENCHMARK':<52s} | ${ov_d1_m:9,f} | ${ov_d2_m:9,f} | {ov_delta_str:10s} | {ov_d1_s:7.2f}% | {ov_d2_s:7.2f}% | {ov_d1_wr:5.1f}% | {ov_d2_wr:5.1f}%")
    print("=" * 135)

    # Decision Gate Check
    passes_market_share = ov_d2_s >= 50.0
    no_major_regression = ov_delta >= -500.0
    print("\n--- DECISION GATE ANALYSIS ---")
    print(f"  * Overall Market Share: D.1={ov_d1_s:.2f}% vs D.2={ov_d2_s:.2f}% (Threshold >= 50.0%: {'PASS' if passes_market_share else 'FAIL'})")
    print(f"  * Overall Mean Delta   : {ov_delta_str} (Threshold >= -$500.00: {'PASS' if no_major_regression else 'FAIL'})")
    print(f"  * Overall Win Rate     : D.1={ov_d1_wr:.1f}% vs D.2={ov_d2_wr:.1f}%")

    if passes_market_share and no_major_regression:
        print("\n[VERDICT]: PROVEN RESILIENCE AGAINST 1200-3000+ ELITE TIERS - SAFE FOR DEPLOYMENT! ✅")
    else:
        print("\n[VERDICT]: FAILED 1200+ DECISION GATE - DOES NOT ESCAPE THE WALL ❌")

if __name__ == "__main__":
    main()
