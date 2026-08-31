"""EXP122: Late-Game Crop Retirement / Conditional Labor.

Tests whether the Cluster 51 elite advantage comes from late-game crop retirement
and/or worker burst, NOT from early/mid-game strategy changes.

4 Arms:
  A - D.1 Control (unmodified)
  B - Late Crop Retirement Only (stop servicing doomed crops after Day 20)
  C - Late Worker Burst Only (hire 10 workers on Day 28 instead of 2)
  D - Combined Retirement + Worker Burst

Backbone: D.1 unchanged through Day 20. Only late-game behavior varies.

Telemetry: last successful harvest, doomed immature crops, worker utilization,
           cash at D21/D26/D30, terminal stranded crops, final reward, win rate.
"""
from __future__ import annotations
import os, sys, json, gzip, importlib.util, numpy as np, pandas as pd
from collections import defaultdict
from huggingface_hub import hf_hub_download

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

hf_token_path = os.path.expanduser("~/.hf/HF_TOKEN")
HF_TOKEN = None
if os.path.exists(hf_token_path):
    with open(hf_token_path, "r", encoding="utf-8") as f:
        HF_TOKEN = f.read().strip()
    os.environ["HF_TOKEN"] = HF_TOKEN

def get_episode_path(episode_id):
    local_path = os.path.join(EPISODES_DIR, f"{episode_id}.json.gz")
    if os.path.exists(local_path):
        return local_path
    rel_hf_path = f"datasets/il/episodes/{episode_id}.json.gz"
    try:
        return hf_hub_download(repo_id="KiroSamurai/kaggriculture-il", filename=rel_hf_path,
                               repo_type="dataset", local_dir=BASE_DIR, token=HF_TOKEN)
    except Exception:
        return None

def load_replay_actions(episode_path, opp_seat):
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

# Load D.1
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Strawberry spec: first=10, max_yield=4, ongoing=True, harvest every 2 days after first
STRAW_FIRST = 10
STRAW_INTERVAL = 2
STRAW_MAX_YIELD = 4
TERMINAL_STEP = 720  # Day 30 hour 0

class LateGameAgent:
    """D.1 wrapper with late-game crop retirement and/or worker burst."""

    def __init__(self, arm_name, retire_crops=False, worker_burst=False):
        self.arm_name = arm_name
        self.retire_crops = retire_crops
        self.worker_burst = worker_burst
        self.doomed_tiles = set()  # (x,y) tiles we've marked as doomed
        self.last_harvest_step = 0
        self.doomed_count_history = {}

    def act(self, obs, config=None):
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        # Get D.1 base action
        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # === ARM B/D: Late Crop Retirement (after Day 20) ===
        if self.retire_crops and day >= 21:
            player = obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0)
            farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
            farm = farms[player] if len(farms) > player else {}
            tiles = farm.get("tiles", []) or []

            # Identify doomed strawberry tiles
            new_doomed = set()
            for y, row in enumerate(tiles):
                for x, tile in enumerate(row):
                    if not isinstance(tile, dict):
                        continue
                    if tile.get("crop") == "STRAWBERRY" and tile.get("kind") == "PLANT":
                        planted = int(tile.get("planted_day", day))
                        first_harvest_day = planted + STRAW_FIRST
                        days_to_terminal = 30 - day
                        days_to_first = first_harvest_day - day

                        # If crop can't even reach first harvest, or can only get 0-1 harvests
                        if days_to_first > days_to_terminal or (days_to_terminal - days_to_first) < 2:
                            new_doomed.add((x, y))

            self.doomed_tiles.update(new_doomed)

            # Track doomed count at milestones
            if step in [504, 624, 696, 718]:  # D21, D26, D29, D30
                self.doomed_count_history[step] = len(self.doomed_tiles)

            # Filter out hands actions targeting doomed tiles (water/fertilize)
            filtered_hands = []
            for h in hands_act:
                if isinstance(h, (list, tuple)) and len(h) >= 1:
                    # Hand action format: [action, x, y, ...] or [[action, x, y], ...]
                    # Try to extract position
                    pos = None
                    if len(h) >= 3:
                        pos = (h[1], h[2])
                    elif len(h) >= 2 and isinstance(h[1], (list, tuple)) and len(h[1]) >= 2:
                        pos = (h[1][0], h[1][1])

                    if pos and pos in self.doomed_tiles:
                        action_name = h[0] if isinstance(h[0], str) else ""
                        if action_name in ("WATER", "FERTILIZE", "PLANT"):
                            continue  # Skip servicing doomed tiles
                filtered_hands.append(h)
            hands_act = filtered_hands

        # === ARM C/D: Worker Burst (Day 28+) ===
        if self.worker_burst and day >= 28:
            # Add HIRE orders if we don't have enough workers
            player = obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0)
            farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
            farm = farms[player] if len(farms) > player else {}
            current_hands = len(farm.get("hands", []) or [])
            target_hands = 10

            if current_hands < target_hands:
                # Add HIRE orders (up to market order limit)
                hire_count = min(target_hands - current_hands, 10 - len(market_orders))
                for _ in range(hire_count):
                    market_orders.append(["HIRE"])

        # Track last harvest
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY":
                self.last_harvest_step = step

        # Also check hands for HARVEST actions
        for h in hands_act:
            if isinstance(h, (list, tuple)) and len(h) >= 1:
                action_name = h[0] if isinstance(h[0], str) else ""
                if action_name == "HARVEST":
                    self.last_harvest_step = step

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }


def run_match(agent_inst, replay_actions, seed):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    traj = {
        "cash": {}, "workers": {}, "strawberries": {}, "doomed": {},
        "last_harvest": 0, "terminal_reward": 0.0, "opp_reward": 0.0,
        "share": 0.0, "won": False, "stranded_crops": 0,
    }

    step_idx = 0
    while not env.done:
        obs0 = env.state[0].observation
        farms = obs0.get("farms", [])
        my_farm = farms[0] if len(farms) > 0 else {}
        day = (step_idx // 24) + 1
        money = float(my_farm.get("money", 0.0))
        hands = len(my_farm.get("hands", []))

        if step_idx in [504, 624, 696, 718]:
            d_label = f"D{day}"
            traj["cash"][d_label] = money
            traj["workers"][d_label] = hands
            straw_c = 0
            for row in my_farm.get("tiles", []) or []:
                for t in (row if isinstance(row, list) else [row]):
                    if isinstance(t, dict) and t.get("crop") == "STRAWBERRY" and t.get("kind") == "PLANT":
                        straw_c += 1
            traj["strawberries"][d_label] = straw_c
            traj["doomed"][d_label] = len(agent_inst.doomed_tiles) if hasattr(agent_inst, "doomed_tiles") else 0

        a0 = agent_inst.act(obs0, env.configuration)
        a1 = replay_actions[min(step_idx, len(replay_actions) - 1)]
        env.step([a0, a1])
        step_idx += 1

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)
    pie = r0 + r1

    traj["terminal_reward"] = r0
    traj["opp_reward"] = r1
    traj["share"] = (r0 / pie) * 100.0 if pie > 0 else 50.0
    traj["won"] = r0 > r1
    traj["last_harvest"] = agent_inst.last_harvest_step if hasattr(agent_inst, "last_harvest_step") else 0

    # Count stranded crops at terminal
    obs_final = env.state[0].observation
    farms = obs_final.get("farms", [])
    my_farm = farms[0] if len(farms) > 0 else {}
    stranded = 0
    for row in my_farm.get("tiles", []) or []:
        for t in (row if isinstance(row, list) else [row]):
            if isinstance(t, dict) and t.get("crop") == "STRAWBERRY" and t.get("kind") == "PLANT":
                # Check if it still has unharvested yield
                if int(t.get("yield_units", 0)) > 0:
                    stranded += 1
    traj["stranded_crops"] = stranded

    return traj


def main():
    print("=" * 135)
    print("EXP122: LATE-GAME CROP RETIREMENT / CONDITIONAL LABOR (4 ARMS)")
    print("=" * 135)

    df_index = pd.read_csv(os.path.join(DATASETS_IL, "index.csv"))
    df_clusters = pd.read_csv(os.path.join(DATASETS_IL, "clusters.csv"))
    df_merged = pd.merge(df_clusters, df_index[["episode_id", "seed", "elo_avg"]], on="episode_id")

    # Use same 20 episodes as EXP121
    target_clusters = [87, 59, 84, 76, 73, 51, 95]
    selected = []
    for c in target_clusters:
        c_rows = df_merged[(df_merged["cluster"] == c) & (df_merged["won"] == 1)]
        for _, r in c_rows.head(3).iterrows():
            selected.append({"episode_id": int(r["episode_id"]), "seat": int(r["seat"]),
                             "cluster": int(r["cluster"]), "seed": int(r["seed"]) if pd.notnull(r["seed"]) else 1000 + int(r["episode_id"]) % 5000})
            if len(selected) >= 20:
                break
        if len(selected) >= 20:
            break

    print(f"Selected {len(selected)} elite replay episodes.")

    arms = {
        "A: D.1 Control":            {"retire_crops": False, "worker_burst": False},
        "B: Late Crop Retirement":   {"retire_crops": True,  "worker_burst": False},
        "C: Late Worker Burst":      {"retire_crops": False, "worker_burst": True},
        "D: Combined Retirement+Burst": {"retire_crops": True,  "worker_burst": True},
    }

    arm_results = defaultdict(list)

    for arm_name, params in arms.items():
        print(f"\n>>> Running {arm_name}...")
        for ep_info in selected:
            ep_id = ep_info["episode_id"]
            opp_seat = 1 - ep_info["seat"]  # opponent is the other seat
            seed = ep_info["seed"]

            ep_path = get_episode_path(ep_id)
            if not ep_path:
                continue

            actions, conf_seed = load_replay_actions(ep_path, opp_seat)
            actual_seed = conf_seed if conf_seed is not None else seed

            agent_inst = LateGameAgent(
                arm_name=arm_name,
                retire_crops=params["retire_crops"],
                worker_burst=params["worker_burst"],
            )

            traj = run_match(agent_inst, actions, actual_seed)
            arm_results[arm_name].append({**traj, "episode_id": ep_id, "cluster": ep_info["cluster"]})

            won_str = "WIN" if traj["won"] else "LOSS"
            print(f"  Ep {ep_id} (Clust {ep_info['cluster']}) | Reward=${traj['terminal_reward']:>9,.0f} | Share={traj['share']:4.1f}% ({won_str}) | D21 Straw={traj['strawberries'].get('D21', -1)} D26 Straw={traj['strawberries'].get('D26', -1)} D30 Straw={traj['strawberries'].get('D30', -1)} | Stranded={traj['stranded_crops']}")

    # Summary
    print("\n" + "=" * 135)
    print("EXP122: SUMMARY")
    print("=" * 135)
    print(f"{'Arm':<35s} | {'Mean Reward':>12s} | {'Delta vs A':>10s} | {'Win Rate':>8s} | {'Mean Share':>10s} | {'D21 Straw':>9s} | {'D26 Straw':>9s} | {'D30 Straw':>9s} | {'Stranded':>8s} | {'Last Harvest':>12s}")
    print("-" * 135)

    base_mean = np.mean([t["terminal_reward"] for t in arm_results["A: D.1 Control"]])

    for arm_name, trajs in arm_results.items():
        mean_rew = np.mean([t["terminal_reward"] for t in trajs])
        delta = mean_rew - base_mean
        wr = sum(1 for t in trajs if t["won"]) / len(trajs) * 100
        mean_share = np.mean([t["share"] for t in trajs])
        d21 = np.mean([t["strawberries"].get("D21", 0) for t in trajs])
        d26 = np.mean([t["strawberries"].get("D26", 0) for t in trajs])
        d30 = np.mean([t["strawberries"].get("D30", 0) for t in trajs])
        stranded = np.mean([t["stranded_crops"] for t in trajs])
        last_h = np.mean([t["last_harvest"] for t in trajs])
        delta_str = f"+${delta:,.0f}" if delta >= 0 else f"-${abs(delta):,.0f}"
        print(f"{arm_name:<35s} | ${mean_rew:10,.0f} | {delta_str:>10s} | {wr:6.1f}% | {mean_share:8.1f}% | {d21:9.1f} | {d26:9.1f} | {d30:9.1f} | {stranded:8.1f} | Step {last_h:6.0f}")

    # Save JSON
    out_json = os.path.join(REPORTS_DIR, "exp122_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({arm: [{k: v for k, v in t.items()} for t in trajs] for arm, trajs in arm_results.items()}, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
