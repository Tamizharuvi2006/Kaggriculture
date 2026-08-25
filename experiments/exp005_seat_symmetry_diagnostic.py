"""EXP005: Ground-Truth Seat Symmetry Diagnostic & First Divergence Lab.
Evaluates mirror matches (A vs A) and isolates whether Seat 0 dominance is:
1. Engine lockstep mechanics
2. Observation / player-indexing asymmetry
3. Agent-internal state leakage or ordering bug
"""
from __future__ import annotations
import sys
import os
import copy
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

# 1. Load Baseline Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

# 2. Load APEX v83 Control
spec_v83 = importlib.util.spec_from_file_location("bot_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
bot_v83 = importlib.util.module_from_spec(spec_v83)
spec_v83.loader.exec_module(bot_v83)

# 3. Load AdaptiveAgent
from engine.agent import AdaptiveAgent

def trace_first_divergence(agent_fn_0, agent_fn_1, seed: int = 42, max_steps: int = 720):
    """Steps through a match and pinpoints the exact first turn of divergence."""
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()

    divergence_info = None

    for step in range(max_steps):
        if env.done:
            break

        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = agent_fn_0(obs0)
        act1 = agent_fn_1(obs1)

        # Record pre-step state
        f0 = obs0.farms[0]
        f1 = obs1.farms[1]
        
        m0_pre = float(f0.get("money", 0))
        m1_pre = float(f1.get("money", 0))

        env.step([act0, act1])

        # Record post-step state
        f0_post = env.state[0].observation.farms[0]
        f1_post = env.state[0].observation.farms[1]

        m0_post = float(f0_post.get("money", 0))
        m1_post = float(f1_post.get("money", 0))

        # Check for divergence in money, actions, or inventory
        if divergence_info is None:
            # Action diff
            act0_str = str(act0)
            act1_str = str(act1)
            
            money_diff = abs(m0_post - m1_post) > 1e-4
            action_diff = (act0_str != act1_str)
            
            if money_diff or action_diff:
                divergence_info = {
                    "step": step,
                    "day": step // 24,
                    "hour": step % 24,
                    "money_diff": money_diff,
                    "action_diff": action_diff,
                    "m0_pre": m0_pre,
                    "m1_pre": m1_pre,
                    "m0_post": m0_post,
                    "m1_post": m1_post,
                    "act0": act0,
                    "act1": act1,
                    "market_prices": dict(env.state[0].observation.market.get("prices", {})),
                    "market_inventory": dict(env.state[0].observation.market.get("inventory", {})),
                }

    final_reward0 = float(env.state[0].reward or 0.0)
    final_reward1 = float(env.state[1].reward or 0.0)

    return {
        "seed": seed,
        "reward0": final_reward0,
        "reward1": final_reward1,
        "winner": 0 if final_reward0 > final_reward1 else (1 if final_reward1 > final_reward0 else 0.5),
        "delta": final_reward0 - final_reward1,
        "divergence": divergence_info,
    }

def run_mirror_suite(name: str, agent_fn_builder, seeds: list):
    print(f"\n{'=' * 85}")
    print(f"RUNNING MIRROR SUITE: {name} vs {name} across {len(seeds)} seeds")
    print(f"{'=' * 85}")

    results = []
    seat0_wins = 0
    seat1_wins = 0
    ties = 0
    total_delta = 0.0
    first_div_steps = []

    for s in seeds:
        # Create fresh instances for both seats to prevent any shared memory
        bot0 = agent_fn_builder()
        bot1 = agent_fn_builder()
        
        res = trace_first_divergence(bot0, bot1, seed=s)
        results.append(res)

        if res["winner"] == 0: seat0_wins += 1
        elif res["winner"] == 1: seat1_wins += 1
        else: ties += 1

        total_delta += res["delta"]
        if res["divergence"]:
            first_div_steps.append(res["divergence"]["step"])

        div_step_str = f"Step {res['divergence']['step']}" if res['divergence'] else "None (Exact Match)"
        print(f"Seed {s:>8}: Seat 0 = ${res['reward0']:>10,.2f} | Seat 1 = ${res['reward1']:>10,.2f} | Delta = ${res['delta']:>+10,.2f} | First Div: {div_step_str}")

    print("-" * 85)
    print(f"Summary for {name} Mirror Matches:")
    print(f"  Seat 0 Wins: {seat0_wins}/{len(seeds)} ({seat0_wins/len(seeds):.1%})")
    print(f"  Seat 1 Wins: {seat1_wins}/{len(seeds)} ({seat1_wins/len(seeds):.1%})")
    print(f"  Ties       : {ties}/{len(seeds)}")
    print(f"  Mean Delta : ${total_delta / len(seeds):+,.2f}")
    if first_div_steps:
        print(f"  Earliest Divergence Step: Step {min(first_div_steps)} (Avg Step {sum(first_div_steps)/len(first_div_steps):.1f})")

    return results

def run_exp005():
    print("=" * 85)
    print("EXP005: SEAT SYMMETRY & FIRST DIVERGENCE DIAGNOSTIC BATTERY")
    print("=" * 85)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888, 11111, 22222, 33333, 44444]

    # Test 1: v18 vs v18
    res_v18 = run_mirror_suite("kaitofukami-v18", lambda: bot_v18.agent, test_seeds)

    # Test 2: v83 vs v83
    res_v83 = run_mirror_suite("submission_v83", lambda: bot_v83.agent, test_seeds)

    # Test 3: AdaptiveAgent vs AdaptiveAgent (Fresh Instances)
    res_adapt = run_mirror_suite("AdaptiveAgent", lambda: AdaptiveAgent(enable_forensic_logging=False).act, test_seeds)

    # Detailed Forensic Inspection of Seed 42 First Divergence
    print("\n" + "=" * 85)
    print("DEEP FORENSIC DIVERGENCE INSPECTION: Seed 42 for AdaptiveAgent vs AdaptiveAgent")
    print("=" * 85)
    
    bot_a = AdaptiveAgent()
    bot_b = AdaptiveAgent()
    sample_div = trace_first_divergence(bot_a.act, bot_b.act, seed=42)
    div = sample_div.get("divergence")
    if div:
        print(f"First Divergence occurred at Step {div['step']} (Day {div['day']}, Hour {div['hour']})")
        print(f"  Seat 0 Money Pre/Post: ${div['m0_pre']} -> ${div['m0_post']}")
        print(f"  Seat 1 Money Pre/Post: ${div['m1_pre']} -> ${div['m1_post']}")
        print(f"  Seat 0 Action: {div['act0']}")
        print(f"  Seat 1 Action: {div['act1']}")
        print(f"  Market Prices at Div: {div['market_prices']}")
    else:
        print("No divergence found; trajectory was 100% identical!")

if __name__ == "__main__":
    run_exp005()
