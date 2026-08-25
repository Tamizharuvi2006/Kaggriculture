"""Forensic step-by-step diagnostic of AdaptiveAgent vs Baseline bot."""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

from engine.agent import AdaptiveAgent

spec_v83 = importlib.util.spec_from_file_location("bot_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
bot_v83 = importlib.util.module_from_spec(spec_v83)
spec_v83.loader.exec_module(bot_v83)

def run_diagnostic(seed: int = 42):
    print("=" * 80)
    print(f"RUNNING STEP-BY-STEP FORENSIC MATCH (Seed: {seed})")
    print("=" * 80)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    cand = AdaptiveAgent(enable_forensic_logging=True)

    print(f"{'Step':>5} | {'Day':>3} | {'Cand Money':>11} | {'Ctrl Money':>11} | {'Cand Land':>9} | {'Ctrl Land':>9} | {'Cand Cows':>9} | {'Ctrl Cows':>9} | {'Cand Straw':>10} | {'Ctrl Straw':>10}")
    print("-" * 105)

    step = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = cand.act(obs0)
        act1 = bot_v83.agent(obs1)

        env.step([act0, act1])

        if step % 48 == 0 or env.done:
            f0 = env.state[0].observation.farms[0]
            f1 = env.state[0].observation.farms[1]
            
            m0 = float(f0.get("money", 0))
            m1 = float(f1.get("money", 0))
            
            u0 = len(f0.get("unlocked_quadrants", []))
            u1 = len(f1.get("unlocked_quadrants", []))
            
            # Count cows
            cows0 = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("animal") == "COW")
            cows1 = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("animal") == "COW")
            
            # Count strawberries
            straw0 = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            straw1 = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")

            print(f"{step:5d} | {step//24:3d} | ${m0:10,.0f} | ${m1:10,.0f} | {u0:9d} | {u1:9d} | {cows0:9d} | {cows1:9d} | {straw0:10d} | {straw1:10d}")

        step += 1

    print("\n[Match Complete]")
    print(f"Final Reward Candidate: ${env.state[0].reward:,.2f}")
    print(f"Final Reward Control  : ${env.state[1].reward:,.2f}")
    print(f"Outcome: {'CANDIDATE WON [WIN]' if env.state[0].reward > env.state[1].reward else 'CONTROL WON [LOSS]'}")

if __name__ == "__main__":
    run_diagnostic(42)
