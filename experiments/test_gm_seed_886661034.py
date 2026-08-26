"""EXP077: Direct Simulation on 3011.4-Elo Grandmaster Seed 886661034.

Replays Seed 886661034 (where 3011.4-Elo Tagir Analyzes beat 2856.2-Elo sneaky6767 with $72,403 vs $68,196):
1. Runs Variant D.1 vs kaitofukami-v18 on Seed 886661034 (Seat 0 & Seat 1)
2. Runs Variant D.1 vs Variant D.1 (Mirror) on Seed 886661034
3. Compares D.1's extracted wealth vs Grandmaster Tagir Analyzes' $72,403!
"""
from __future__ import annotations
import sys
import os
import kaggle_environments
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

SEED = 886661034

def run_match(agent0_type, agent1_type, seed):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    a0 = VariantDAgent() if agent0_type == "d1" else bot_v18
    a1 = VariantDAgent() if agent1_type == "d1" else bot_v18

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = a0.act(obs0, env.configuration) if agent0_type == "d1" else a0.agent(obs0)
        act1 = a1.act(obs1, env.configuration) if agent1_type == "d1" else a1.agent(obs1)

        env.step([act0, act1])

    return float(env.state[0].reward or 0.0), float(env.state[1].reward or 0.0)

def main():
    print("=" * 105)
    print(f"EXP077: 3011.4-ELO GRANDMASTER SEED SIMULATION (SEED {SEED})")
    print("=" * 105)
    print("Historical Live Match in Kaggle:")
    print("  Seat 0: sneaky6767 (2856.2 Elo)   -> $68,196.00")
    print("  Seat 1: Tagir Analyzes (3011.4 Elo)-> $72,403.00 (Winner)")
    print("  Combined Economy Realized          : $140,599.00\n")

    # Match 1: D.1 (Seat 0) vs v18 (Seat 1)
    r0, r1 = run_match("d1", "v18", SEED)
    print(f"Simulation 1: D.1 (Seat 0) vs v18 (Seat 1)")
    print(f"  D.1 Bank (Seat 0): ${r0:,.2f} | v18 Bank (Seat 1): ${r1:,.2f} | Margin: ${r0-r1:+,.2f} | Winner: {'D.1' if r0 > r1 else 'v18'}")

    # Match 2: v18 (Seat 0) vs D.1 (Seat 1)
    r0, r1 = run_match("v18", "d1", SEED)
    print(f"\nSimulation 2: v18 (Seat 0) vs D.1 (Seat 1)")
    print(f"  v18 Bank (Seat 0): ${r0:,.2f} | D.1 Bank (Seat 1): ${r1:,.2f} | Margin: ${r1-r0:+,.2f} | Winner: {'D.1' if r1 > r0 else 'v18'}")

    # Match 3: D.1 vs D.1 (Mirror)
    r0, r1 = run_match("d1", "d1", SEED)
    print(f"\nSimulation 3: D.1 vs D.1 (True Mirror)")
    print(f"  D.1 (Seat 0): ${r0:,.2f} | D.1 (Seat 1): ${r1:,.2f} | Combined: ${r0+r1:,.2f}")

    print("\n" + "=" * 105)
    print("GRANDMASTER BENCHMARK VERDICT:")
    print(f"  - Grandmaster Tagir Analyzes (3011.4 Elo) extracted $72,403.00 on Seed {SEED}.")
    print(f"  - Variant D.1 extracted ${max(r0, r1):,.2f} in mirror / direct duel.")
    print("=" * 105)

if __name__ == "__main__":
    main()
