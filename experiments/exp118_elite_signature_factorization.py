"""EXP118: Elite Signature Factorization & Trajectory Forensics Suite.

Evaluates the 5 factorized arms of the elite macro signature against D.1 Control A:
- Arm A (Control): Standard D.1 baseline (13 workers, 8 cows, 0 sheep, Day 18 cutoff, End dump).
- Arm B (Labor Economy): 13 workers -> 9 workers (cap hands at 9).
- Arm C (Livestock Synergy): +4 sheep (dual cow 8 + sheep 4 livestock herd).
- Arm D (Extended Horizon): Day-18 -> Day-26 crop planting cutoff.
- Arm E (Continuous Liquidity): Continuous mid-game micro-selling (Days 10-25).
- Arm F (Full Combined Package): B + C + D + E.
- Arm G (Non-destructive Package): 9 workers + 4 sheep + Day-26 planting + continuous selling (Strawberry core preserved).

Tested across 3 distinct cohorts:
1. Apex Elite Cluster 87 seeds (Replay matches)
2. High-Frequency Winning Cluster 59/73/84 seeds
3. Fresh Saturated Control seeds

Tracks full trajectories at Days 5, 10, 15, 20, 25, 30:
- Cash ($), Workers, Cows, Sheep, Strawberries, Sales events, Terminal Bank ($), Market Share (%), Win Rate (%).
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
    except Exception as e:
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

class FactorizedAgent:
    """Agent implementing specific factorized modifications over D.1."""
    def __init__(self, arm_name: str, max_hands: int = 13, target_sheep: int = 0, last_plant_day: int = 18, continuous_sales: bool = False):
        self.arm_name = arm_name
        self.max_hands = max_hands
        self.target_sheep = target_sheep
        self.last_plant_day = last_plant_day
        self.continuous_sales = continuous_sales
        self.price_history = {"STRAWBERRY": [], "MILK": [], "WOOL": []}
        self.bought_sheep = 0

    def act(self, obs: dict, config: dict | None = None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
        my_farm = farms[0] if len(farms) > 0 else {}
        money = float(my_farm.get("money", 0.0))
        shed = my_farm.get("shed", {}) or {}
        hands = len(my_farm.get("hands", []))

        # 1. Base D.1 action
        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Arm B & F & G: Cap Worker Hiring at max_hands
        if self.max_hands < 13:
            filtered_orders = []
            for m in market_orders:
                if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE":
                    if hands >= self.max_hands:
                        continue
                filtered_orders.append(m)
            market_orders = filtered_orders

        # Arm C & F & G: Add Sheep Acquisition (Days 8-12)
        if self.target_sheep > 0 and self.bought_sheep < self.target_sheep:
            if 8 <= day <= 12 and money >= 600.0:
                if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "SHEEP" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_ANIMAL", "SHEEP", 1])
                        self.bought_sheep += 1

        # Arm D & F & G: Extended Planting Cutoff (Buy seeds through Day 26 if tiles empty)
        if self.last_plant_day > 18 and 18 < day <= self.last_plant_day:
            straw_seeds = shed.get("STRAWBERRY_SEED", 0)
            if straw_seeds < 8 and money >= 200.0:
                if not any(len(m) >= 2 and m[0] == "BUY_SEED" and m[1] == "STRAWBERRY" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", 4])

        # Arm E & F & G: Continuous Mid-Game Micro-Selling (Days 10-25)
        if self.continuous_sales and 10 <= day <= 25:
            # Monetize Milk, Wool, Strawberry in small batches
            for item in ("MILK", "WOOL", "STRAWBERRY"):
                qty = shed.get(item, 0)
                if qty >= 3:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

        # Arm G: Preserves core strawberry allocation and terminal clearance (Step 696)
        if step >= 696:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = shed.get(item, 0)
                if qty > 0:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_trajectory_match(agent_inst, replay_actions, seed: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    traj = {
        "cash": {},
        "workers": {},
        "cows": {},
        "sheep": {},
        "strawberries": {},
        "sales_count": 0,
        "terminal_reward": 0.0,
        "opp_reward": 0.0,
        "share": 0.0,
        "won": False,
    }

    step_idx = 0
    while not env.done:
        obs0 = env.state[0].observation
        farms = obs0.get("farms", [])
        my_farm = farms[0] if len(farms) > 0 else {}
        day = (step_idx // 24) + 1

        money = float(my_farm.get("money", 0.0))
        hands = len(my_farm.get("hands", []))

        # Sample at milestone days: 5, 10, 15, 20, 25, 30
        if step_idx in [120, 240, 360, 480, 600, 718]:
            d_label = f"D{day}"
            traj["cash"][d_label] = money
            traj["workers"][d_label] = hands

            cow_c = 0
            sheep_c = 0
            straw_c = 0
            for row in my_farm.get("tiles", []) or []:
                for t in row if isinstance(row, list) else [row]:
                    if isinstance(t, dict):
                        a = str(t.get("animal", "")).upper()
                        c = str(t.get("crop", "")).upper()
                        if a == "COW": cow_c += 1
                        elif a == "SHEEP": sheep_c += 1
                        if c == "STRAWBERRY": straw_c += 1
            traj["cows"][d_label] = cow_c
            traj["sheep"][d_label] = sheep_c
            traj["strawberries"][d_label] = straw_c

        a0 = agent_inst.act(obs0, env.configuration)
        a1 = replay_actions[min(step_idx, len(replay_actions) - 1)]

        # Track sales events
        for m in a0.get("market") or []:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL":
                traj["sales_count"] += 1

        env.step([a0, a1])
        step_idx += 1

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)
    pie = r0 + r1

    traj["terminal_reward"] = r0
    traj["opp_reward"] = r1
    traj["share"] = (r0 / pie) * 100.0 if pie > 0 else 50.0
    traj["won"] = r0 > r1

    return traj

def main():
    print("=" * 125)
    print("EXP118: ELITE SIGNATURE FACTORIZATION & TRAJECTORY FORENSICS (7 ARMS)")
    print("=" * 125)

    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[['episode_id', 'seed', 'elo_avg']], on='episode_id')

    # Select representative episodes
    clust87_samples = df_merged[df_merged['cluster'] == 87].head(3)
    clust59_samples = df_merged[df_merged['cluster'] == 59].head(3)
    clust84_samples = df_merged[df_merged['cluster'] == 84].head(3)

    test_episodes = []
    for _, r in pd.concat([clust87_samples, clust59_samples, clust84_samples]).iterrows():
        test_episodes.append({
            "episode_id": int(r['episode_id']),
            "seat": int(r['seat']),
            "cluster": int(r['cluster']),
            "seed": int(r['seed']) if pd.notnull(r['seed']) else 1000 + int(r['episode_id']) % 5000,
        })

    print(f"Total Test Episodes: {len(test_episodes)} (Cluster 87, 59, 84)")

    # Define the 7 Factorized Arms
    arms = {
        "Arm A: D.1 Control A":               {"max_hands": 13, "target_sheep": 0, "last_plant_day": 18, "continuous_sales": False},
        "Arm B: 9 Workers (Labor Economy)":   {"max_hands": 9,  "target_sheep": 0, "last_plant_day": 18, "continuous_sales": False},
        "Arm C: +4 Sheep (Livestock Synergy)": {"max_hands": 13, "target_sheep": 4, "last_plant_day": 18, "continuous_sales": False},
        "Arm D: Day-26 Plant (Extend Horizon)":{"max_hands": 13, "target_sheep": 0, "last_plant_day": 26, "continuous_sales": False},
        "Arm E: Continuous Mid-Game Sales":   {"max_hands": 13, "target_sheep": 0, "last_plant_day": 18, "continuous_sales": True},
        "Arm F: Full Combined Package (B+C+D+E)":{"max_hands": 9, "target_sheep": 4, "last_plant_day": 26, "continuous_sales": True},
        "Arm G: Non-Destructive Package":     {"max_hands": 9,  "target_sheep": 4, "last_plant_day": 24, "continuous_sales": True},
    }

    arm_trajectories = defaultdict(list)

    for arm_name, params in arms.items():
        print(f"\n>>> Running Evaluation: {arm_name}...")
        for ep_info in test_episodes:
            ep_id = ep_info["episode_id"]
            opp_seat = ep_info["seat"]
            seed = ep_info["seed"]

            ep_path = get_episode_path(ep_id)
            if not ep_path:
                continue

            actions, conf_seed = load_replay_actions(ep_path, opp_seat)
            actual_seed = conf_seed if conf_seed is not None else seed

            agent_inst = FactorizedAgent(
                arm_name=arm_name,
                max_hands=params["max_hands"],
                target_sheep=params["target_sheep"],
                last_plant_day=params["last_plant_day"],
                continuous_sales=params["continuous_sales"],
            )

            traj = run_trajectory_match(agent_inst, actions, actual_seed)
            arm_trajectories[arm_name].append(traj)

            delta = traj["terminal_reward"] - 0.0
            won_str = "WIN" if traj["won"] else "LOSS"
            print(f"  Ep {ep_id} (Clust {ep_info['cluster']}) | Reward=${traj['terminal_reward']:9,f} | Share={traj['share']:4.1f}% ({won_str}) | D15 Cash=${traj['cash'].get('D15', 0):6,.0f} | D20 Cash=${traj['cash'].get('D20', 0):6,.0f}")

    # ====================================================================================================
    # TRAJECTORY & FACTOR ATTRIBUTION SUMMARY
    # ====================================================================================================
    print("\n" + "=" * 135)
    print("EXP118: FACTOR ATTRIBUTION & TRAJECTORY MILESTONE SUMMARY")
    print("=" * 135)
    print(f"{'Factorized Arm':<38s} | {'Terminal Mean':<13s} | {'Net Delta':<10s} | {'Share':<7s} | {'Win Rate':<8s} | {'D10 Cash':<9s} | {'D15 Cash':<9s} | {'D20 Cash':<9s} | {'D25 Cash':<9s}")
    print("-" * 135)

    base_mean = np.mean([t["terminal_reward"] for t in arm_trajectories["Arm A: D.1 Control A"]])

    for arm_name, trajs in arm_trajectories.items():
        mean_rew = np.mean([t["terminal_reward"] for t in trajs])
        mean_share = np.mean([t["share"] for t in trajs])
        wr = (sum(1 for t in trajs if t["won"]) / len(trajs)) * 100.0
        delta = mean_rew - base_mean
        delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"

        c_d10 = np.mean([t["cash"].get("D10", 0) for t in trajs])
        c_d15 = np.mean([t["cash"].get("D15", 0) for t in trajs])
        c_d20 = np.mean([t["cash"].get("D20", 0) for t in trajs])
        c_d25 = np.mean([t["cash"].get("D25", 0) for t in trajs])

        print(f"{arm_name[:38]:<38s} | ${mean_rew:11,f} | {delta_str:10s} | {mean_share:5.1f}% | {wr:6.1f}% | ${c_d10:7,.0f} | ${c_d15:7,.0f} | ${c_d20:7,.0f} | ${c_d25:7,.0f}")

    print("=" * 135)

if __name__ == "__main__":
    main()
