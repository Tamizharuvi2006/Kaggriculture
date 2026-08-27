"""EXP119: Continuous-Selling Alpha & Price-Realization Trajectory Suite.

Scientific Hypothesis (GLM-5.2 + Gemini 3.7 Convergence):
- Does continuous mid-game selling actually generate positive alpha (higher realized prices / reinvestment velocity),
  or does it merely move the same revenue earlier in time?

Candidates Evaluated:
1. Control A: D.1 Standard Baseline (Batch >= 4 / Endgame Clearance)
2. Candidate D.4-Continuous: Unconditional Micro-Sales Cadence (Shed >= 2 continuously)
3. Candidate D.4-Elastic: Price-Momentum Continuous Selling (Front-run price drops, sell >= 2)
4. Candidate D.4-VolumeVelocity: Floor-Protected Instant Liquidation (Sell all if P >= floor)

Benchmark Configuration:
- Paired, Seat-Balanced Evaluation: 60 matches (30 seeds x 2 seats) vs kaitofukami-v18
- Plus Elite Replay Cohort: 18 matches across Cluster 87, 59, 84
- Total: 78 matches per candidate (312 full 720-step simulation runs)

Telemetry Tracked:
- Realized Average Sale Price ($/unit) for STRAWBERRY, MILK, WOOL
- Cumulative Cash Trajectory at Days 5, 10, 15, 20, 25, 30
- Market Share Trajectory (%)
- Total Transaction Event Count
- Mean Terminal Bank ($) & Net Paired Delta ($)
- Win Rate (%) & Loss Margin ($)
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

import kaggle_environments

DATASETS_IL = os.path.join(BASE_DIR, "datasets", "il")
EPISODES_DIR = os.path.join(DATASETS_IL, "episodes")
os.makedirs(EPISODES_DIR, exist_ok=True)

# Load HF Token
hf_token_path = os.path.expanduser("~/.hf/HF_TOKEN")
HF_TOKEN = None
if os.path.exists(hf_token_path):
    with open(hf_token_path, "r", encoding="utf-8") as f:
        HF_TOKEN = f.read().strip()
    os.environ["HF_TOKEN"] = HF_TOKEN

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
    except Exception:
        return None

def load_replay_actions(episode_path: str, opp_seat: int):
    with gzip.open(episode_path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    steps = data.get("steps", [])
    actions = []
    for s in steps:
        if isinstance(s, list) and len(s) > opp_seat:
            act = s[opp_seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}
            actions.append(act)
        else:
            actions.append({"farmer": ["PASS"], "hands": [], "market": []})
    seed = data.get("configuration", {}).get("seed")
    return actions, seed

# Load Baseline D.1 Module
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

class V18Adapter:
    def act(self, obs, config=None):
        return bot_v18_mod.agent(obs)
    def reset(self):
        pass

bot_v18 = V18Adapter()

class ContinuousSellingAgent:
    """Configurable Selling Cadence Agent."""
    def __init__(self, mode: str = "control"):
        self.mode = mode
        self.price_history = defaultdict(list)

    def reset(self):
        self.price_history = defaultdict(list)

    def act(self, obs: dict, config: dict | None = None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
        market_obs = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {})
        my_farm = farms[0] if len(farms) > 0 else {}
        shed = my_farm.get("shed", {}) or {}

        # Track prices
        for item, p in market_obs.items():
            if isinstance(p, (int, float)):
                self.price_history[item].append(float(p))

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        if self.mode == "control":
            # Pure D.1 Control
            return base_act

        elif self.mode == "continuous_micro":
            # Mode B: Unconditional Micro-Sales (Shed >= 2 anytime Days 6-29)
            if 6 <= day <= 29:
                for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL", "EGG", "WHEAT"):
                    qty = shed.get(item, 0)
                    if qty >= 2:
                        if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

        elif self.mode == "elastic_momentum":
            # Mode C: Price-Momentum Elastic Selling
            if 6 <= day <= 29:
                for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                    qty = shed.get(item, 0)
                    if qty >= 2:
                        hist = self.price_history.get(item, [])
                        curr_p = hist[-1] if len(hist) > 0 else 100.0
                        prev_p = hist[-2] if len(hist) > 1 else curr_p
                        velocity = curr_p - prev_p

                        # Sell aggressively if price is high or dropping (front-run crash)
                        if curr_p >= 120.0 or velocity <= 0.0 or qty >= 6:
                            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                                if len(market_orders) < 10:
                                    market_orders.append(["SELL", item, qty])

        elif self.mode == "volume_velocity":
            # Mode D: Floor-Protected Instant Liquidation
            if 6 <= day <= 29:
                floors = {"STRAWBERRY": 95.0, "MILK": 85.0, "TOMATO": 70.0, "CARROT": 50.0, "WOOL": 110.0}
                for item, floor_p in floors.items():
                    qty = shed.get(item, 0)
                    if qty >= 2:
                        curr_p = float(market_obs.get(item, 100.0))
                        if curr_p >= floor_p or qty >= 8:
                            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                                if len(market_orders) < 10:
                                    market_orders.append(["SELL", item, qty])

        # Endgame Clearance (Step >= 696)
        if step >= 696:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = shed.get(item, 0)
                if qty > 0:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_telemetry_match(agent_0, agent_1, seed: int, is_replay: bool = False, replay_acts: list | None = None):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    if hasattr(agent_0, "reset"): agent_0.reset()
    if hasattr(agent_1, "reset"): agent_1.reset()

    traj = {
        "cash": {},
        "share": {},
        "sales_events": 0,
        "sold_units": defaultdict(int),
        "revenue_items": defaultdict(float),
        "terminal_reward_0": 0.0,
        "terminal_reward_1": 0.0,
        "won": False,
    }

    step_idx = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        farms = obs0.get("farms", [])
        mkt = obs0.get("market", {})
        my_farm = farms[0] if len(farms) > 0 else {}
        opp_farm = farms[1] if len(farms) > 1 else {}
        day = (step_idx // 24) + 1

        c0 = float(my_farm.get("money", 0.0))
        c1 = float(opp_farm.get("money", 0.0))
        tot_c = c0 + c1

        # Track trajectory milestones
        if step_idx in [120, 240, 360, 480, 600, 718]:
            d_label = f"D{day}"
            traj["cash"][d_label] = c0
            traj["share"][d_label] = (c0 / tot_c * 100.0) if tot_c > 0 else 50.0

        a0 = agent_0.act(obs0, env.configuration)
        if is_replay and replay_acts:
            a1 = replay_acts[min(step_idx, len(replay_acts) - 1)]
        else:
            a1 = agent_1.act(obs1, env.configuration)

        # Track transactions and realized prices
        for m in a0.get("market") or []:
            if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                item = m[1]
                qty = int(m[2])
                p = float(mkt.get(item, 0.0))
                traj["sales_events"] += 1
                traj["sold_units"][item] += qty
                traj["revenue_items"][item] += (qty * p)

        env.step([a0, a1])
        step_idx += 1

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    traj["terminal_reward_0"] = r0
    traj["terminal_reward_1"] = r1
    traj["won"] = r0 > r1
    return traj

def main():
    print("=" * 135)
    print("EXP119: CONTINUOUS-SELLING ALPHA & PRICE-REALIZATION TRAJECTORY SUITE")
    print("=" * 135)

    candidates = {
        "D.1 Control A (Batch >= 4 / Endgame Dump)": "control",
        "D.4-Continuous (Unconditional Micro Cadence)": "continuous_micro",
        "D.4-Elastic (Price-Momentum Micro Selling)": "elastic_momentum",
        "D.4-VolumeVelocity (Floor-Protected Instant)": "volume_velocity",
    }

    # Benchmark Seeds (25 paired seeds = 50 matches per candidate)
    seeds = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010,
             2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
             3001, 3002, 3003, 3004, 3005]

    # Elite Replay Episodes (6 representative episodes = 6 matches per candidate)
    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[['episode_id', 'seed', 'elo_avg']], on='episode_id')

    replay_samples = []
    for c in [87, 59, 84]:
        for _, r in df_merged[df_merged['cluster'] == c].head(2).iterrows():
            replay_samples.append({
                "episode_id": int(r['episode_id']),
                "seat": int(r['seat']),
                "cluster": int(r['cluster']),
                "seed": int(r['seed']) if pd.notnull(r['seed']) else 1000 + int(r['episode_id']) % 5000,
            })

    print(f"Evaluation Matrix: {len(seeds)*2} Paired v18 Matches + {len(replay_samples)} Elite Replay Matches = {len(seeds)*2 + len(replay_samples)} Matches per Candidate")

    results = {}

    for cand_name, mode in candidates.items():
        print(f"\n>>> Running Candidate Evaluation: {cand_name}...")
        cand_agent = ContinuousSellingAgent(mode=mode)
        trajs = []

        # 1. Paired Benchmark vs v18 (Seat 0 & Seat 1)
        for s in seeds:
            # Seat 0
            t0 = run_telemetry_match(cand_agent, bot_v18, s)
            trajs.append(t0)
            # Seat 1 (Inverted)
            t1 = run_telemetry_match(bot_v18, cand_agent, s)
            # Invert t1 perspective so candidate is player 0
            t1_inv = {
                "cash": t1["cash"],
                "share": {k: 100.0 - v for k, v in t1["share"].items()},
                "sales_events": t1["sales_events"],
                "sold_units": t1["sold_units"],
                "revenue_items": t1["revenue_items"],
                "terminal_reward_0": t1["terminal_reward_1"],
                "terminal_reward_1": t1["terminal_reward_0"],
                "won": t1["terminal_reward_1"] > t1["terminal_reward_0"],
            }
            trajs.append(t1_inv)

        # 2. Elite Replay Benchmark
        for ep_info in replay_samples:
            ep_id = ep_info["episode_id"]
            opp_seat = ep_info["seat"]
            seed = ep_info["seed"]
            ep_path = get_episode_path(ep_id)
            if ep_path:
                actions, conf_seed = load_replay_actions(ep_path, opp_seat)
                act_seed = conf_seed if conf_seed is not None else seed
                t_rep = run_telemetry_match(cand_agent, None, act_seed, is_replay=True, replay_acts=actions)
                trajs.append(t_rep)

        results[cand_name] = trajs

        mean_rew = np.mean([t["terminal_reward_0"] for t in trajs])
        wr = (sum(1 for t in trajs if t["won"]) / len(trajs)) * 100.0
        events = np.mean([t["sales_events"] for t in trajs])
        print(f"  Summary: Mean Reward=${mean_rew:,.2f} | Win Rate={wr:4.1f}% | Avg Sales Events={events:3.1f}")

    # ====================================================================================================
    # COMPREHENSIVE EXPERIMENT REPORT & PRICE REALIZATION TABLE
    # ====================================================================================================
    print("\n" + "=" * 145)
    print("EXP119: CANDIDATE PERFORMANCE & PRICE REALIZATION SUMMARY")
    print("=" * 145)
    print(f"{'Candidate Policy':<42s} | {'Mean Bank':<12s} | {'Delta':<10s} | {'Win Rate':<8s} | {'Events':<6s} | {'Straw Price':<11s} | {'Milk Price':<10s} | {'D15 Cash':<9s} | {'D20 Cash':<9s}")
    print("-" * 145)

    base_mean = np.mean([t["terminal_reward_0"] for t in results["D.1 Control A (Batch >= 4 / Endgame Dump)"]])

    for cand_name, trajs in results.items():
        mean_rew = np.mean([t["terminal_reward_0"] for t in trajs])
        delta = mean_rew - base_mean
        delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"
        wr = (sum(1 for t in trajs if t["won"]) / len(trajs)) * 100.0
        events = np.mean([t["sales_events"] for t in trajs])

        # Realized Price per Commodity
        tot_straw_u = sum(t["sold_units"]["STRAWBERRY"] for t in trajs)
        tot_straw_r = sum(t["revenue_items"]["STRAWBERRY"] for t in trajs)
        p_straw = (tot_straw_r / tot_straw_u) if tot_straw_u > 0 else 0.0

        tot_milk_u = sum(t["sold_units"]["MILK"] for t in trajs)
        tot_milk_r = sum(t["revenue_items"]["MILK"] for t in trajs)
        p_milk = (tot_milk_r / tot_milk_u) if tot_milk_u > 0 else 0.0

        c_d15 = np.mean([t["cash"].get("D15", 0) for t in trajs])
        c_d20 = np.mean([t["cash"].get("D20", 0) for t in trajs])

        print(f"{cand_name[:42]:<42s} | ${mean_rew:10,.2f} | {delta_str:10s} | {wr:6.1f}% | {events:6.1f} | ${p_straw:9.2f} | ${p_milk:8.2f} | ${c_d15:7,.0f} | ${c_d20:7,.0f}")

    print("=" * 145)

if __name__ == "__main__":
    main()
