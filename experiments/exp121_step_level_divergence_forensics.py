"""EXP121: Step-Level Divergence Forensics Suite.

Extracts empirical, step-by-step (0-719) forensic comparisons between real elite replay agents
and D.1 Control A (submission_clean.py) on identical seeds, seats, and opponent action trajectories.

Objectives:
1. Identify 20 representative high-Elo elite episodes across elite clusters (Clusters 87, 59, 84, 76, 73, etc.)
2. Replay D.1 against identical opponent actions on the exact same seed and seat.
3. Record:
   - First Action Divergence (Step, Day, Action Category, Exact Action Difference)
   - First State Divergence (Step, Day, State Component, Magnitude)
   - Step-by-Step Trajectory of Cash, Land, Animals, Crops, Shed, and Market Orders
   - Divergence Precedence: Does divergence occur before Day 5, Days 6-10, Days 11-20, or Endgame?
   - Statistical Distribution & Pattern Mining across all 20 episodes.
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
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(EPISODES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

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

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def extract_farm_metrics(farm_dict: dict) -> dict:
    if not isinstance(farm_dict, dict):
        return {"money": 0.0, "hands": 0, "cows": 0, "sheep": 0, "crops": defaultdict(int), "shed": {}}
    money = float(farm_dict.get("money", 0.0))
    hands = len(farm_dict.get("hands", []))
    shed = farm_dict.get("shed", {}) or {}

    cows = 0
    sheep = 0
    crops = defaultdict(int)
    for row in farm_dict.get("tiles", []) or []:
        for t in (row if isinstance(row, list) else [row]):
            if isinstance(t, dict):
                a = str(t.get("animal", "")).upper()
                c = str(t.get("crop", "")).upper()
                if a == "COW": cows += 1
                elif a == "SHEEP": sheep += 1
                if c and c != "NONE":
                    crops[c] += 1

    return {
        "money": money,
        "hands": hands,
        "cows": cows,
        "sheep": sheep,
        "crops": crops,
        "shed": shed,
    }

def actions_are_equal(act_a: dict, act_b: dict) -> bool:
    if not isinstance(act_a, dict) or not isinstance(act_b, dict):
        return act_a == act_b
    farmer_a = act_a.get("farmer") or ["PASS"]
    farmer_b = act_b.get("farmer") or ["PASS"]
    if list(farmer_a) != list(farmer_b):
        return False

    hands_a = [list(h) for h in (act_a.get("hands") or [])]
    hands_b = [list(h) for h in (act_b.get("hands") or [])]
    if hands_a != hands_b:
        return False

    market_a = [list(m) for m in (act_a.get("market") or [])]
    market_b = [list(m) for m in (act_b.get("market") or [])]
    if market_a != market_b:
        return False

    return True

def classify_action_divergence(act_d1: dict, act_elite: dict) -> str:
    mkt_d1 = act_d1.get("market") or []
    mkt_elite = act_elite.get("market") or []

    # Check land purchases
    land_d1 = any(len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt_d1)
    land_el = any(len(m) >= 1 and m[0] == "BUY_LAND" for m in mkt_elite)
    if land_d1 != land_el:
        return "LAND_EXPANSION_TIMING"

    # Check worker hiring
    hire_d1 = any(len(m) >= 1 and m[0] == "HIRE" for m in mkt_d1)
    hire_el = any(len(m) >= 1 and m[0] == "HIRE" for m in mkt_elite)
    if hire_d1 != hire_el:
        return "WORKER_HIRING_RAMP"

    # Check animal buying
    anim_d1 = [m[1] for m in mkt_d1 if len(m) >= 2 and m[0] == "BUY_ANIMAL"]
    anim_el = [m[1] for m in mkt_elite if len(m) >= 2 and m[0] == "BUY_ANIMAL"]
    if anim_d1 != anim_el:
        return "LIVESTOCK_SELECTION_OR_TIMING"

    # Check seed buying
    seed_d1 = [m[1] for m in mkt_d1 if len(m) >= 2 and m[0] == "BUY_SEED"]
    seed_el = [m[1] for m in mkt_elite if len(m) >= 2 and m[0] == "BUY_SEED"]
    if seed_d1 != seed_el:
        return "CROP_SEED_PORTFOLIO"

    # Check selling orders
    sell_d1 = [m[1] for m in mkt_d1 if len(m) >= 2 and m[0] == "SELL"]
    sell_el = [m[1] for m in mkt_elite if len(m) >= 2 and m[0] == "SELL"]
    if sell_d1 != sell_el:
        return "MARKET_SELLING_CADENCE"

    # Check farmer action
    farmer_d1 = act_d1.get("farmer") or ["PASS"]
    farmer_el = act_elite.get("farmer") or ["PASS"]
    if list(farmer_d1) != list(farmer_el):
        return "FARMER_MICRO_PATHING"

    # Check hands action
    hands_d1 = act_d1.get("hands") or []
    hands_el = act_elite.get("hands") or []
    if hands_d1 != hands_el:
        return "WORKER_TASK_ALLOCATION"

    return "OTHER_ACTION_DIFF"

def run_forensic_replay(episode_id: int, elite_seat: int, cluster_id: int):
    ep_path = get_episode_path(episode_id)
    if not ep_path:
        return None

    with gzip.open(ep_path, "rt", encoding="utf-8") as f:
        ep_data = json.load(f)

    steps = ep_data.get("steps", [])
    conf = ep_data.get("configuration", {})
    seed = conf.get("seed", 1000 + episode_id % 5000)
    opp_seat = 1 - elite_seat

    elite_acts = []
    opp_acts = []
    elite_states = []

    for s in steps:
        if isinstance(s, list) and len(s) > 1:
            elite_act = s[elite_seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}
            opp_act = s[opp_seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}
            elite_obs = s[elite_seat].get("observation") or {}
            elite_acts.append(elite_act)
            opp_acts.append(opp_act)
            elite_states.append(elite_obs)

    # Initialize Environment for D.1
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    forensic_log = {
        "episode_id": episode_id,
        "cluster": cluster_id,
        "elite_seat": elite_seat,
        "seed": seed,
        "elite_terminal_reward": float(ep_data.get("rewards", [0, 0])[elite_seat] if "rewards" in ep_data else steps[-1][elite_seat].get("reward", 0.0)),
        "d1_terminal_reward": 0.0,
        "first_action_divergence": None,
        "first_state_divergence": None,
        "divergences_by_day": defaultdict(int),
        "divergence_categories": defaultdict(int),
        "milestone_snapshots": {},
    }

    first_act_div = None
    first_state_div = None

    for t in range(min(720, len(steps))):
        if env.done:
            break
        obs_d1_0 = env.state[elite_seat].observation
        opp_obs = env.state[opp_seat].observation

        day = (t // 24) + 1
        hour = t % 24

        # D.1 Act
        act_d1 = sub_d1.agent(obs_d1_0, env.configuration)
        act_elite = elite_acts[t] if t < len(elite_acts) else {"farmer": ["PASS"], "hands": [], "market": []}
        act_opp = opp_acts[t] if t < len(opp_acts) else {"farmer": ["PASS"], "hands": [], "market": []}

        # Check Action Divergence
        if not actions_are_equal(act_d1, act_elite):
            category = classify_action_divergence(act_d1, act_elite)
            forensic_log["divergences_by_day"][f"Day_{day:02d}"] += 1
            forensic_log["divergence_categories"][category] += 1

            if first_act_div is None:
                first_act_div = {
                    "step": t,
                    "day": day,
                    "hour": hour,
                    "category": category,
                    "act_d1": act_d1,
                    "act_elite": act_elite,
                }

        # Check State Divergence
        farms_d1 = obs_d1_0.get("farms", [])
        m_d1 = extract_farm_metrics(farms_d1[elite_seat] if len(farms_d1) > elite_seat else {})

        farms_el = elite_states[t].get("farms", []) if t < len(elite_states) else []
        m_el = extract_farm_metrics(farms_el[elite_seat] if len(farms_el) > elite_seat else {})

        if first_state_div is None and (abs(m_d1["money"] - m_el["money"]) > 10.0 or m_d1["cows"] != m_el["cows"] or m_d1["hands"] != m_el["hands"] or m_d1["crops"] != m_el["crops"]):
            first_state_div = {
                "step": t,
                "day": day,
                "hour": hour,
                "d1_money": m_d1["money"],
                "elite_money": m_el["money"],
                "d1_hands": m_d1["hands"],
                "elite_hands": m_el["hands"],
                "d1_cows": m_d1["cows"],
                "elite_cows": m_el["cows"],
                "d1_crops": dict(m_d1["crops"]),
                "elite_crops": dict(m_el["crops"]),
            }

        # Milestone Day Snapshots
        if t in [24, 72, 120, 240, 360, 480, 600, 718]:
            d_str = f"D{day}"
            forensic_log["milestone_snapshots"][d_str] = {
                "d1": {"money": m_d1["money"], "hands": m_d1["hands"], "cows": m_d1["cows"], "strawberries": m_d1["crops"].get("STRAWBERRY", 0)},
                "elite": {"money": m_el["money"], "hands": m_el["hands"], "cows": m_el["cows"], "strawberries": m_el["crops"].get("STRAWBERRY", 0)},
            }

        # Step Environment: D.1 is at elite_seat, opp is at opp_seat
        joint_action = [None, None]
        joint_action[elite_seat] = act_d1
        joint_action[opp_seat] = act_opp
        env.step(joint_action)
        if env.done:
            break

    r_d1 = float(env.state[elite_seat].reward or 0.0)
    forensic_log["d1_terminal_reward"] = r_d1
    forensic_log["first_action_divergence"] = first_act_div
    forensic_log["first_state_divergence"] = first_state_div

    return forensic_log

def main():
    print("=" * 135)
    print("EXP121: STEP-LEVEL DIVERGENCE FORENSICS SUITE (20 ELITE REPLAY EPISODES)")
    print("=" * 135)

    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[['episode_id', 'seed', 'elo_avg']], on='episode_id')

    # Select 20 elite episodes across top clusters
    target_clusters = [87, 59, 84, 76, 73, 51, 95]
    selected_episodes = []
    
    for c in target_clusters:
        c_rows = df_merged[(df_merged['cluster'] == c) & (df_merged['won'] == 1)]
        for _, r in c_rows.head(3).iterrows():
            selected_episodes.append({
                "episode_id": int(r['episode_id']),
                "seat": int(r['seat']),
                "cluster": int(r['cluster']),
                "reward": float(r['reward']),
            })
            if len(selected_episodes) >= 20:
                break
        if len(selected_episodes) >= 20:
            break

    print(f"Selected {len(selected_episodes)} Elite Winning Replay Episodes across Clusters {list(set(e['cluster'] for e in selected_episodes))}.")
    print("-" * 135)
    print(f"{'Episode ID':<12s} | {'Cluster':<8s} | {'Seat':<5s} | {'Elite Reward':<13s} | {'D.1 Reward':<12s} | {'Delta (Elite - D1)':<20s} | {'First Act Div Step':<19s} | {'First Act Category':<28s}")
    print("-" * 135)

    forensic_results = []

    for item in selected_episodes:
        ep_id = item["episode_id"]
        seat = item["seat"]
        clust = item["cluster"]

        f_res = run_forensic_replay(ep_id, seat, clust)
        if not f_res:
            continue

        forensic_results.append(f_res)

        el_rew = f_res["elite_terminal_reward"]
        d1_rew = f_res["d1_terminal_reward"]
        delta = el_rew - d1_rew
        delta_str = f"+${delta:,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"

        first_act = f_res["first_action_divergence"]
        first_step_str = f"Step {first_act['step']:3d} (D{first_act['day']}H{first_act['hour']})" if first_act else "None"
        first_cat_str = first_act["category"] if first_act else "None"

        print(f"{ep_id:<12d} | {clust:<8d} | {seat:<5d} | ${el_rew:11,.2f} | ${d1_rew:10,.2f} | {delta_str:<20s} | {first_step_str:<19s} | {first_cat_str:<28s}")

    # ====================================================================================================
    # STATISTICAL SYNTHESIS REPORT
    # ====================================================================================================
    print("\n" + "=" * 135)
    print("EXP121: STATISTICAL SYNTHESIS & DIVERGENCE TAXONOMY")
    print("=" * 135)

    # 1. First Action Divergence Step Distribution
    first_steps = [f["first_action_divergence"]["step"] for f in forensic_results if f["first_action_divergence"]]
    first_days = [f["first_action_divergence"]["day"] for f in forensic_results if f["first_action_divergence"]]
    first_cats = [f["first_action_divergence"]["category"] for f in forensic_results if f["first_action_divergence"]]

    cat_counts = pd.Series(first_cats).value_counts()
    print("\n1. PRIMARY ROOT DIVERGENCE CATEGORIES (First Action Diff):")
    for cat, cnt in cat_counts.items():
        pct = (cnt / len(first_cats)) * 100.0
        print(f"   - {cat:<32s}: {cnt:2d} matches ({pct:4.1f}%)")

    print(f"\n2. DIVERGENCE TIMING DISTRIBUTION:")
    print(f"   - Mean First Action Divergence Step : Step {np.mean(first_steps):.1f} (Day {np.mean(first_days):.1f})")
    print(f"   - Median First Action Divergence Step: Step {np.median(first_steps):.1f} (Day {np.median(first_days):.1f})")
    print(f"   - Min Step: Step {np.min(first_steps)} | Max Step: Step {np.max(first_steps)}")

    # 3. Save Structured JSON Artifact for Full Downstream Analysis
    out_json = os.path.join(REPORTS_DIR, "exp121_step_level_divergence_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(forensic_results, f, indent=2)
    print(f"\nSaved Full Structured Step-Level Dataset: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
