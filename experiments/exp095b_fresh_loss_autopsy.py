"""EXP095b: Micro-Autopsy of the 2 Fresh Large-Deficit Defeats (Ep 100412460 & 100435254).

Downloads the exact episode replay JSON from Kaggle API for:
1. Episode 100412460 (Opponent 55804001, Elo 1106.4, Deficit -$28,053)
2. Episode 100435254 (Opponent 55804467, Elo 1037.6, Deficit -$25,055)

Dissects:
- Opponent Land Expansion & Coordinates
- Opponent Crop Portfolio (Strawberries vs Melons vs Tomatoes vs Carrots vs Wheat)
- Opponent Livestock (Cows vs Sheep vs Chickens)
- Opponent Labor (Worker count & assignments)
- Exact Step of First Economic Separation
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

TARGET_EPISODES = [100412460, 100435254]
CACHE_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches")
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_episode_replay(ep_id: int):
    local_file = os.path.join(CACHE_DIR, f"episode_{ep_id}.json")
    if os.path.exists(local_file):
        with open(local_file, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisodeReplay?episodeId={ep_id}"
    print(f"Fetching replay for Episode {ep_id} from Kaggle API...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        with open(local_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data

def dissect_replay(ep_id: int):
    data = fetch_episode_replay(ep_id)
    steps = data.get("steps", [])
    if not steps:
        print(f"No step data in Episode {ep_id}.")
        return

    print("=" * 105)
    print(f"MICRO-AUTOPSY: EPISODE {ep_id} ({len(steps)} STEPS)")
    print("=" * 105)

    # Determine agent seats
    # State 0 vs State 1
    init_state = steps[0]
    agents = data.get("agents", [])
    sub_0 = agents[0].get("submissionId") if len(agents) > 0 else None
    sub_1 = agents[1].get("submissionId") if len(agents) > 1 else None

    d1_seat = 0 if sub_0 == 55780289 else 1
    opp_seat = 1 - d1_seat

    print(f"  * D.1 Seat: Player {d1_seat} | Opponent Seat: Player {opp_seat} (Sub ID: {agents[opp_seat].get('submissionId')}, Rating: {agents[opp_seat].get('initialScore')})")

    # Track final rewards
    final_step = steps[-1]
    d1_rew = final_step[d1_seat].get("reward")
    opp_rew = final_step[opp_seat].get("reward")
    print(f"  * Final Outcome: D.1 ${d1_rew:,.0f} vs Opponent ${opp_rew:,.0f} (Deficit: ${d1_rew - opp_rew:+,.0f})")

    # Sample checkpoints: Step 72 (Day 3), 120 (Day 5), 240 (Day 10), 360 (Day 15), 480 (Day 20), 600 (Day 25), 719 (Day 30)
    print("\n--- OPPONENT STATE PROFILE ACROSS CHECKPOINTS ---")
    print(f"{'Step / Day':<15} | {'D.1 Money':>12} | {'Opp Money':>12} | {'Margin':>10} | {'Opp Sunk Assets / Notes'}")
    print("-" * 105)

    for s_idx in [72, 120, 240, 360, 480, 600, 696, len(steps)-1]:
        if s_idx >= len(steps):
            continue
        step_entry = steps[s_idx]
        obs = step_entry[0].get("observation", {})
        farms = obs.get("farms", [])

        if len(farms) > max(d1_seat, opp_seat):
            d1_f = farms[d1_seat]
            opp_f = farms[opp_seat]

            d1_m = d1_f.get("money", 0)
            opp_m = opp_f.get("money", 0)

            opp_workers = len(opp_f.get("workers", []))
            opp_cows = len(opp_f.get("cows", []))
            opp_plots = len(opp_f.get("plots", []))
            opp_tiles = len(opp_f.get("tiles", []))

            # Check crops on plots
            crop_types = {}
            for p in opp_f.get("plots", []):
                ctype = p.get("type", "UNKNOWN")
                crop_types[ctype] = crop_types.get(ctype, 0) + 1

            crop_str = ", ".join([f"{k}:{v}" for k, v in crop_types.items()]) if crop_types else "None"
            notes = f"W:{opp_workers} Cows:{opp_cows} Plots:{opp_plots} ({crop_str})"

            print(f"Step {s_idx:<4} (Day {s_idx//24:<2}) | ${d1_m:>11,.0f} | ${opp_m:>11,.0f} | ${d1_m - opp_m:>+9,.0f} | {notes}")

def run_exp095b():
    for ep_id in TARGET_EPISODES:
        try:
            dissect_replay(ep_id)
        except Exception as e:
            print(f"Error dissecting episode {ep_id}: {e}")

if __name__ == "__main__":
    run_exp095b()
