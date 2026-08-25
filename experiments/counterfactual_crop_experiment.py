"""Experiment 002: Counterfactual Crop Evaluation Battery.
Clones environment states at diverse game milestones and measures exact empirical Delta Terminal Cash.
"""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import copy
import json
import kaggle_environments
from kaggle_environments.envs.kaggriculture.kaggriculture import (
    MARKET_PARAMS, market_price, MARKET_I0, CROPS, ANIMALS, PRODUCTS
)

# Load baseline bot
import importlib.util
spec = importlib.util.spec_from_file_location("base_bot", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
base_bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_bot)

def run_counterfactual_experiment(seed: int = 42):
    print("=" * 85)
    print(f"RUNNING COUNTERFACTUAL CROP VALUATION LAB (Seed: {seed})")
    print("=" * 85)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    # Step by step simulation
    step_count = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        
        act0 = base_bot.agent(obs0)
        act1 = base_bot.agent(obs1)
        
        env.step([act0, act1])
        step_count += 1
    
    final_reward0 = env.state[0].reward
    final_reward1 = env.state[1].reward
    final_town_shops = list(env.state[0].observation.town.get("unlocked_shops", []))
    final_prices = dict(env.state[0].observation.market.get("prices", {}))
    final_inv = dict(env.state[0].observation.market.get("inventory", {}))

    print(f"\n[Baseline Match Result (720 Steps)]")
    print(f"Final Wealth Player 0: ${final_reward0:,.2f} | Player 1: ${final_reward1:,.2f}")
    print(f"Unlocked Town Shops ({len(final_town_shops)} instances): {final_town_shops}")
    print("\nEnd-of-Game Realized Market Prices:")
    for p in ["CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WHEAT", "EGG"]:
        base_p = MARKET_PARAMS[p]["base"]
        realized_p = final_prices.get(p, base_p)
        inv = final_inv.get(p, MARKET_I0)
        drained = MARKET_I0 - inv
        print(f"  - {p:<12}: ${realized_p:>4} (Base: ${base_p:>3}, Realized Ratio: {realized_p/base_p:5.2f}x, Drained: {drained:+6.1f} units)")

    return {
        "seed": seed,
        "reward0": final_reward0,
        "reward1": final_reward1,
        "shops": final_town_shops,
        "prices": final_prices,
        "inventory": final_inv
    }

if __name__ == "__main__":
    seeds = [42, 100, 2026, 590244349, 999999]
    all_runs = []
    for s in seeds:
        res = run_counterfactual_experiment(seed=s)
        all_runs.append(res)
