"""Surgical A/B Testing Harness for Candidate L+ End-Game & Pasture Optimizations.
"""

import sys
import os
import json
import glob
import time
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import kaggle_environments
    HAS_KAGGLE_ENV = True
except ImportError:
    HAS_KAGGLE_ENV = False

# Exact seeds from the narrow loss replays
TARGET_MATCHES = [
    ("91282953.json (-$1.3k Loss)", 590244349),
    ("91292018.json (-$200 Loss)", 855978439),
    ("91287496.json (-$692 Loss)", 1745977583),
    ("91286593.json (-$2.5k Loss)", 91286593),
]

def load_agent(agent_file, name_prefix):
    spec = importlib.util.spec_from_file_location(name_prefix, agent_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def run_simulation(agent_file, seed):
    if not HAS_KAGGLE_ENV:
        return None
    try:
        agent_fn = load_agent(agent_file, f"agent_{seed}_{os.path.basename(agent_file)}")
        opponent_file = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
        opp_fn = load_agent(opponent_file, f"opp_{seed}")
        
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([agent_fn, opp_fn])
        
        steps = env.steps
        last_step = steps[-1]
        p0 = float(last_step[0]["observation"]["farms"][0]["money"])
        p1 = float(last_step[1]["observation"]["farms"][1]["money"])
        
        # Track last sell step for our agent (Player 0)
        last_sell_step = None
        for s_idx, step in enumerate(steps):
            act = step[0].get("action", {})
            market = act.get("market", []) if isinstance(act, dict) else []
            has_sell = any(isinstance(ord, list) and len(ord) >= 1 and ord[0] == "SELL" for ord in market)
            if has_sell:
                last_sell_step = s_idx

        # Track unharvested inventory on step 720
        farm0 = last_step[0]["observation"]["farms"][0]
        inventory = farm0.get("inventory", {})
        stranded_items = {k: v for k, v in inventory.items() if v > 0}

        return {
            "our_wealth": p0,
            "opp_wealth": p1,
            "delta": p0 - p1,
            "last_sell_step": last_sell_step if last_sell_step is not None else 0,
            "stranded_inventory": stranded_items,
        }
    except Exception as e:
        print(f"    Simulation error for {os.path.basename(agent_file)} on seed {seed}: {e}")
        return None

def main():
    print("====================================================")
    print("⚔️ SURGICAL A/B BENCHMARK HARNESS FOR CANDIDATE L+")
    print("====================================================")
    print(f"Kaggle Environments Engine Loaded: {HAS_KAGGLE_ENV}")

    path_control = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    path_eg = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus_eg.py")
    path_ph = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus_ph.py")

    candidates = {
        "L+ Control": path_control,
        "L+ EG Guard": path_eg,
        "L+ PH Priority": path_ph
    }

    results_table = []

    print("\n--- NARROW LOSS REPLAY SEED A/B EVALUATION ---")
    for match_name, seed in TARGET_MATCHES:
        print(f"\nTarget Match: {match_name} (Seed: {seed})")
        row = {"match": match_name, "seed": seed, "candidates": {}}
        
        control_wealth = None

        for c_name, c_path in candidates.items():
            if os.path.exists(c_path):
                res = run_simulation(c_path, seed)
                if res:
                    our = res["our_wealth"]
                    opp = res["opp_wealth"]
                    delta = res["delta"]
                    last_sell = res["last_sell_step"]
                    stranded = res["stranded_inventory"]

                    if c_name == "L+ Control":
                        control_wealth = our

                    iso_delta = (our - control_wealth) if control_wealth is not None else 0.0
                    status = "🏆 WIN" if delta > 0 else "🔴 LOSS"

                    row["candidates"][c_name] = res
                    row["candidates"][c_name]["iso_delta"] = iso_delta

                    print(f"  {c_name:<16}: Our: ${our:9,.2f} | Opp: ${opp:9,.2f} | Net Margin: ${delta:+8,.2f} ({status}) | Last Sell: Step {last_sell:3d} | Iso Delta: ${iso_delta:+7,.2f} | Stranded: {stranded}")
                else:
                    print(f"  {c_name:<16}: (Simulation failed)")
        results_table.append(row)

    print("\n====================================================")
    print("📊 AGGREGATE SURGICAL A/B SCORECARD")
    print("====================================================")
    for c_name in candidates:
        total_wealth = 0.0
        total_delta = 0.0
        total_wins = 0
        total_iso_delta = 0.0
        count = 0

        for r in results_table:
            c_data = r["candidates"].get(c_name)
            if c_data:
                count += 1
                total_wealth += c_data["our_wealth"]
                total_delta += c_data["delta"]
                total_iso_delta += c_data.get("iso_delta", 0.0)
                if c_data["delta"] > 0:
                    total_wins += 1

        if count > 0:
            avg_wealth = total_wealth / count
            avg_delta = total_delta / count
            win_rate = (total_wins / count) * 100
            print(f"Candidate: {c_name:<16} | Avg Wealth: ${avg_wealth:10,.2f} | Avg Net Margin: ${avg_delta:+9,.2f} | Win Rate: {total_wins}/{count} ({win_rate:5.1f}%) | Total Iso Delta: ${total_iso_delta:+9,.2f}")

if __name__ == "__main__":
    main()
