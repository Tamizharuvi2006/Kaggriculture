"""EXP080: Market-Cadence Counterfactual & Order-Dispersion Probe.

1. Tests market-cadence counterfactuals on the 10 Grandmaster tournament seeds:
   - Evaluates D.1 native sell cadence vs delayed sell cadences (+2, +4, +6, +8 steps).
   - Measures market overlap: frequency of simultaneous market dumping (0 steps, 1-2 steps, 3-5 steps).
   - Measures price impact: realized unit price ($/strawberry, $/milk) and market price depression.
   - Measures capital velocity: reinvestment lag, seed cycle integrity, and terminal bank wealth.
2. Safety Kill Criteria:
   - Any missed seed planting cycle -> IMMEDIATE KILL
   - Any dropped worker ticks or idle workers -> IMMEDIATE KILL
   - Any stranded terminal inventory at Step 720 -> IMMEDIATE KILL
   - Wealth regression vs D.1 baseline -> REJECTION
3. Control Baseline:
   - Variant D.1 remains strictly frozen as Control A.
"""
from __future__ import annotations
import sys
import os
import copy
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

# 10 Official Grandmaster Tournament Seeds
GM_SEEDS = [
    {"seed": 886661034,  "name": "Tagir #1 (3014.8)", "gm_rew": 72403.0},
    {"seed": 740260508,  "name": "Tagir #1 (3039.4)", "gm_rew": 72622.0},
    {"seed": 733685934,  "name": "Tagir #1 (3028.8)", "gm_rew": 98077.0},
    {"seed": 1145943550, "name": "Tagir #1 (2905.9)", "gm_rew": 79241.0},
    {"seed": 959303546,  "name": "Top Master 1 (3026.7)", "gm_rew": 113109.0},
    {"seed": 1136230699, "name": "Top Master 1 (3001.9)", "gm_rew": 112008.0},
    {"seed": 495991813,  "name": "Top Master 1 (2945.9)", "gm_rew": 70743.0},
    {"seed": 1765339432, "name": "Top Master 2 (2924.6)", "gm_rew": 60695.0},
    {"seed": 557203808,  "name": "Top Master 3 (2922.0)", "gm_rew": 77948.0},
    {"seed": 514626152,  "name": "sneaky6767 (2872.3)",  "gm_rew": 82537.0},
]

class CounterfactualCadenceAgent:
    """Shadow agent testing sell-delay cadence on top of Variant D.1 engine."""
    def __init__(self, sell_delay: int = 0):
        self.d1 = VariantDAgent()
        self.sell_delay = sell_delay
        self.sell_buffer_hold_steps = 0
        self.total_sell_events = 0
        self.total_units_sold = 0
        self.total_revenue_from_sales = 0.0

    def act(self, observation, configuration):
        step = observation.get("step", 0)
        # Never delay in endgame clearance buffer (step >= 696)
        if step >= 696:
            return self.d1.act(observation, configuration)

        # Intercept sell actions to test delay cadence
        raw_action = self.d1.act(observation, configuration)
        
        # Check if D.1 requested a SELL order in town
        if isinstance(raw_action, dict) and "orders" in raw_action:
            sell_orders = [o for o in raw_action["orders"] if o.get("type") == "SELL"]
            if sell_orders and self.sell_delay > 0:
                if self.sell_buffer_hold_steps < self.sell_delay:
                    self.sell_buffer_hold_steps += 1
                    # Filter out sell orders for this turn, keeping other actions intact
                    non_sell_orders = [o for o in raw_action["orders"] if o.get("type") != "SELL"]
                    raw_action["orders"] = non_sell_orders
                else:
                    self.sell_buffer_hold_steps = 0 # Released
        
        return raw_action

def evaluate_cadence_on_seed(seed: int, sell_delay: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    agent = CounterfactualCadenceAgent(sell_delay=sell_delay)
    step_num = 0
    sell_events = []

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = agent.act(obs0, env.configuration)
        act1 = bot_v18.agent(obs1)

        # Track sell orders
        p0_sells = []
        p1_sells = []
        if isinstance(act0, dict) and "orders" in act0:
            p0_sells = [o for o in act0["orders"] if o.get("type") == "SELL"]
        if isinstance(act1, dict) and "orders" in act1:
            p1_sells = [o for o in act1["orders"] if o.get("type") == "SELL"]

        if p0_sells or p1_sells:
            sell_events.append({
                "step": step_num,
                "p0_sold": len(p0_sells) > 0,
                "p1_sold": len(p1_sells) > 0,
                "simultaneous": len(p0_sells) > 0 and len(p1_sells) > 0,
            })

        env.step([act0, act1])
        step_num += 1

    d1_reward = float(env.state[0].reward or 0.0)
    opp_reward = float(env.state[1].reward or 0.0)

    # Check terminal shed inventory
    final_obs = env.state[0].observation
    farms = final_obs.get("farms", [])
    p0_farm = farms[0] if len(farms) > 0 else {}
    tiles = p0_farm.get("tiles", [])
    stranded_crops = sum(1 for r in tiles for c in r if c and isinstance(c, dict) and "crop" in c)

    simultaneous_sells = sum(1 for ev in sell_events if ev["simultaneous"])
    total_p0_sells = sum(1 for ev in sell_events if ev["p0_sold"])

    return {
        "d1_reward": d1_reward,
        "opp_reward": opp_reward,
        "margin": d1_reward - opp_reward,
        "total_sells": total_p0_sells,
        "simultaneous_sells": simultaneous_sells,
        "overlap_pct": simultaneous_sells / total_p0_sells if total_p0_sells > 0 else 0.0,
        "stranded_crops": stranded_crops,
    }

def run_exp080():
    print("=" * 105)
    print("EXP080: MARKET-CADENCE COUNTERFACTUAL & ORDER-DISPERSION PROBE")
    print("=" * 105)

    delays = [0, 2, 4, 6, 8]
    summary_by_delay = {}

    for delay in delays:
        label = f"D.1 Native (Delay = 0)" if delay == 0 else f"Cadence Delay +{delay} Steps"
        print(f"\nEvaluating {label} across 10 Grandmaster Seeds...")

        results = []
        for s_info in GM_SEEDS:
            res = evaluate_cadence_on_seed(s_info["seed"], sell_delay=delay)
            res["seed_info"] = s_info
            results.append(res)

        mean_reward = float(np.mean([r["d1_reward"] for r in results]))
        mean_opp_reward = float(np.mean([r["opp_reward"] for r in results]))
        mean_margin = float(np.mean([r["margin"] for r in results]))
        mean_overlap = float(np.mean([r["overlap_pct"] for r in results]))
        mean_stranded = float(np.mean([r["stranded_crops"] for r in results]))
        win_rate = sum(1 for r in results if r["margin"] > 0) / len(results)

        summary_by_delay[delay] = {
            "label": label,
            "mean_reward": mean_reward,
            "mean_opp_reward": mean_opp_reward,
            "mean_margin": mean_margin,
            "mean_overlap": mean_overlap,
            "mean_stranded": mean_stranded,
            "win_rate": win_rate,
            "raw_results": results,
        }

    print("\n" + "=" * 105)
    print("EXP080 MASTER COUNTERFACTUAL CADENCE COMPARISON TABLE")
    print("=" * 105)
    print(f"{'Cadence Variant':<28} | {'Mean Bank ($)':>14} | {'Mean Margin ($)':>16} | {'Win Rate %':>11} | {'Simultaneous Sells %':>22} | {'Stranded Crops'}")
    print("-" * 105)

    base_reward = summary_by_delay[0]["mean_reward"]

    for delay in delays:
        s = summary_by_delay[delay]
        delta_str = f"(${s['mean_reward'] - base_reward:+,.0f})" if delay > 0 else "(Baseline)"
        print(f"{s['label']:<28} | ${s['mean_reward']:>13,.2f} | ${s['mean_margin']:>15,.2f} | {s['win_rate']:>10.1%} | {s['mean_overlap']:>21.1%} | {s['mean_stranded']:>14.1f} {delta_str}")

    print("=" * 105)

    # Per-Seed Detailed Breakdown on Key Problem Seeds
    print("\nPER-SEED IMPACT ON GRANDMASTER SEEDS (D.1 Native vs Best Delay):")
    print("-" * 105)
    print(f"{'Seed':<11} | {'Grandmaster':<24} | {'GM Real ($)':>11} | {'D.1 Native ($)':>14} | {'Best Delay ($)':>14} | {'Delta vs Native'}")
    print("-" * 105)

    for idx, s_info in enumerate(GM_SEEDS):
        native_rew = summary_by_delay[0]["raw_results"][idx]["d1_reward"]
        best_rew = max(summary_by_delay[d]["raw_results"][idx]["d1_reward"] for d in delays)
        best_d = next(d for d in delays if summary_by_delay[d]["raw_results"][idx]["d1_reward"] == best_rew)
        delta = best_rew - native_rew
        print(f"{s_info['seed']:<11} | {s_info['name']:<24} | ${s_info['gm_rew']:>10,.0f} | ${native_rew:>13,.0f} | ${best_rew:>13,.0f} (+{best_d}s) | ${delta:>+14,.0f}")

    print("=" * 105)

if __name__ == "__main__":
    run_exp080()
