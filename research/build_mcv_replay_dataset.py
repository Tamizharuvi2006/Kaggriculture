"""APEX 3.0: Historical Replay Dataset Extraction Engine.
Parses local Kaggle replay logs (l+reviews, l++reviews) into state-action-outcome tuples
for empirical Marginal Counterfactual Value (MCV) calibration.
"""

from __future__ import annotations
import sys
import os
import json
import glob
from typing import Dict, List, Any, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from apex.world_model import WorldState

class MCVReplayExtractor:
    """Extracts state-conditioned action outcomes across historical replay trajectories."""

    @staticmethod
    def find_all_replays() -> List[str]:
        search_dirs = [
            os.path.join(BASE_DIR, "l+reviews"),
            os.path.join(BASE_DIR, "l+reviews", "newl"),
            os.path.join(BASE_DIR, "l+reviews", "newl", "loss"),
            os.path.join(BASE_DIR, "l++reviews"),
            os.path.join(BASE_DIR, "l++reviews", "loss"),
        ]
        all_replays = []
        for sdir in search_dirs:
            if os.path.exists(sdir):
                for fpath in glob.glob(os.path.join(sdir, "*.json")):
                    fname = os.path.basename(fpath)
                    if fname.endswith("-0.json") or fname.endswith("-1.json"):
                        continue
                    all_replays.append(fpath)
        return sorted(list(set(all_replays)))

    @staticmethod
    def extract_tuples_from_replay(fpath: str) -> List[Dict[str, Any]]:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        steps = data.get("steps", [])
        if len(steps) < 720:
            return []

        last_step = steps[-1]
        p0_final = float(last_step[0]["observation"]["farms"][0].get("money", 0.0))
        p1_final = float(last_step[1]["observation"]["farms"][1].get("money", 0.0))

        results = []

        for p_idx in [0, 1]:
            my_final = p0_final if p_idx == 0 else p1_final
            opp_final = p1_final if p_idx == 0 else p0_final
            won = my_final >= opp_final

            for step_idx in range(50, 650, 10): # Sample every 10 steps in mid-game
                step_obj = steps[step_idx]
                obs = step_obj[p_idx].get("observation", {})
                act = step_obj[p_idx].get("action", {})

                if not obs or "farms" not in obs:
                    continue

                wstate = WorldState(obs)
                market_act = act.get("market", []) if isinstance(act, dict) else []

                # Downstream outcomes (24 steps later = 1 day, 120 steps later = 5 days)
                step_24 = min(719, step_idx + 24)
                step_120 = min(719, step_idx + 120)

                obs_24 = steps[step_24][p_idx].get("observation", {})
                obs_120 = steps[step_120][p_idx].get("observation", {})

                wealth_24 = float(obs_24.get("farms", [{}])[p_idx].get("money", wstate.money)) if len(obs_24.get("farms", [])) > p_idx else wstate.money
                wealth_120 = float(obs_120.get("farms", [{}])[p_idx].get("money", wstate.money)) if len(obs_120.get("farms", [])) > p_idx else wstate.money

                tuple_record = {
                    "file": os.path.basename(fpath),
                    "player_idx": p_idx,
                    "step": step_idx,
                    "day": wstate.day,
                    "cash": wstate.money,
                    "inventory": wstate.inventory,
                    "num_workers": len(wstate.workers),
                    "num_tiles": len(wstate.tiles),
                    "market_prices": wstate.prices,
                    "executed_market_action": market_act,
                    "downstream_wealth_24": wealth_24,
                    "downstream_wealth_120": wealth_120,
                    "final_wealth": my_final,
                    "won_match": won,
                }
                results.append(tuple_record)

        return results

def main():
    print("==================================================================================", flush=True)
    print("🟣 APEX 3.0: HISTORICAL REPLAY DATASET EXTRACTION ENGINE", flush=True)
    print("==================================================================================", flush=True)

    replays = MCVReplayExtractor.find_all_replays()
    print(f"Found {len(replays)} historical replay files across review repositories.", flush=True)

    all_tuples = []
    for idx, rpath in enumerate(replays, start=1):
        tuples = MCVReplayExtractor.extract_tuples_from_replay(rpath)
        all_tuples.extend(tuples)

    out_dir = os.path.join(BASE_DIR, "data", "replay")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mcv_replay_dataset.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_tuples, f, indent=2)

    print(f"\nExtracted {len(all_tuples)} state-action-outcome tuples from {len(replays)} replays.")
    print(f"Saved dataset to: {out_path}", flush=True)

    # Quick Summary Statistics
    if all_tuples:
        market_actions = [t for t in all_tuples if len(t["executed_market_action"]) > 0]
        sells = [t for t in market_actions if t["executed_market_action"][0][0] == "SELL"]
        print(f"  Total Market Actions Sampled: {len(market_actions)}")
        print(f"  Total SELL Actions Sampled: {len(sells)}")
        print("==================================================================================", flush=True)

if __name__ == "__main__":
    main()
