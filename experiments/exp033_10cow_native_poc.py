"""EXP033: Track B (10-Cow & 12-Cow Native Pasture Proof-of-Concept).
Directly activates the native APEX 14-site pasture pipeline for 10 and 12 cows:
- Control: 8 Cows (Baseline D.1)
- Candidate 10-Cow: 10 Cows (expands to SW pasture site)
- Candidate 12-Cow: 12 Cows (expands to SW pasture site)
Measures:
1. Exact milk and fertilizer collected
2. Net terminal wealth (Target: +$2,000+ vs Control)
3. Win rate vs kaitofukami-v18
"""
from __future__ import annotations
import sys
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

def make_native_cow_agent(cows: int):
    """Creates an agent instance configured with native cow scaling."""
    # Configure global strategy for this agent
    apex4_mod.configure_strategy({"cows": cows})

    def _act(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict):
            return base_act

        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Disciplined Selling (qty >= 4)
        for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
            qty = int(shed.get(item, 0) or 0)
            if qty >= 4:
                if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["SELL", item, qty])

        # Step 696 Clearance
        if step >= 696:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = int(shed.get(item, 0) or 0)
                if qty > 0:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }
    return _act

def run_exp033():
    print("=" * 105)
    print("EXP033: TRACK B (10-COW & 12-COW NATIVE PASTURE PROOF-OF-CONCEPT)")
    print("=" * 105)

    seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 22222]

    configs = [
        ("Control (Variant D.1: 8 Cows)", 8),
        ("Candidate POC (10 Cows)", 10),
        ("Candidate POC (12 Cows)", 12),
    ]

    results = []

    for name, cow_count in configs:
        cand_banks = []
        wins = 0.0
        for s in seeds:
            agent_fn = make_native_cow_agent(cow_count)
            # Match 1: Cand = Seat 0, v18 = Seat 1
            env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env1.reset()
            while not env1.done:
                env1.step([agent_fn(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
            r_c_s0 = float(env1.state[0].reward or 0.0)
            r_v_s1 = float(env1.state[1].reward or 0.0)
            if r_c_s0 > r_v_s1: wins += 1.0
            elif r_c_s0 == r_v_s1: wins += 0.5

            # Match 2: v18 = Seat 0, Cand = Seat 1
            env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env2.reset()
            while not env2.done:
                env2.step([bot_v18.agent(env2.state[0].observation), agent_fn(env2.state[1].observation)])
            r_v_s0 = float(env2.state[0].reward or 0.0)
            r_c_s1 = float(env2.state[1].reward or 0.0)
            if r_c_s1 > r_v_s0: wins += 1.0
            elif r_c_s1 == r_v_s0: wins += 0.5

            cand_banks.extend([r_c_s0, r_c_s1])

        arr = np.array(cand_banks)
        mean_b = float(np.mean(arr))
        med_b = float(np.median(arr))
        max_b = float(np.max(arr))
        min_b = float(np.min(arr))
        p10_b = float(np.percentile(arr, 10))
        p90_b = float(np.percentile(arr, 90))
        win_r = wins / (len(seeds) * 2)

        results.append({
            "name": name,
            "cows": cow_count,
            "mean": mean_b, "median": med_b,
            "max": max_b, "min": min_b,
            "p10": p10_b, "p90": p90_b,
            "win_rate": win_r,
        })
        print(f"  [DONE] {name:<35} -> Mean: ${mean_b:>10,.2f} | Peak: ${max_b:>10,.2f} | Win%: {win_r:>6.1%}")

    print("\n" + "=" * 105)
    print("EXP033 PROOF-OF-CONCEPT REPORT (16 Matches per Candidate on 8 Holdout Seeds)")
    print("=" * 105)
    print(f"{'Configuration':<35} | {'Mean Bank':>12} | {'Median':>12} | {'Floor (Min)':>12} | {'Peak (Max)':>12} | {'Win Rate':>10}")
    print("-" * 105)

    ctrl = results[0]
    for r in results:
        delta_str = f"({r['mean'] - ctrl['mean']:>+8,.2f})" if r != ctrl else "(Baseline)"
        print(f"{r['name']:<35} | ${r['mean']:>11,.2f} | ${r['median']:>11,.2f} | ${r['min']:>11,.2f} | ${r['max']:>11,.2f} | {r['win_rate']:>9.1%} {delta_str}")

    print("\n" + "=" * 105)
    best = max(results, key=lambda x: x["mean"])
    if best['mean'] > ctrl['mean'] + 2000.0:
        print(f">>> VERDICT: 10-COW POC SUCCEEDED! (Promoted to Track B Baseline: +${best['mean'] - ctrl['mean']:,.2f})")
    elif best['mean'] > ctrl['mean']:
        print(f">>> VERDICT: MODEST GAIN (+${best['mean'] - ctrl['mean']:,.2f}), evaluate deeper holdouts.")
    else:
        print(f">>> VERDICT: 10-COW EXPANSION DOES NOT BEAT 8-COW D.1. (KILL LIVESTOCK EXPANSION)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp033()
