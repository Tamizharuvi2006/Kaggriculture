"""EXP006: Trajectory Attribution & Cumulative Margin Decomposition.
Traces turn-by-turn physical state and decomposes final wealth into concrete economic drivers.
"""
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

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

def run_trajectory_attribution(seed: int = 42, opp_bot = bot_v83, opp_name: str = "submission_v83"):
    print("=" * 90)
    print(f"EXP006: TRAJECTORY ATTRIBUTION LAB (Seed: {seed} | Opponent: {opp_name})")
    print("=" * 90)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    cand = AdaptiveAgent(enable_forensic_logging=True)

    # Track metrics across milestones
    milestones = [0, 48, 96, 144, 192, 240, 288, 360, 432, 504, 576, 648, 719]
    history = []

    step = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = cand.act(obs0)
        act1 = opp_bot.agent(obs1)

        env.step([act0, act1])

        if step in milestones or env.done:
            f0 = env.state[0].observation.farms[0]
            f1 = env.state[0].observation.farms[1]
            
            m0 = float(f0.get("money", 0))
            m1 = float(f1.get("money", 0))
            delta = m0 - m1

            u0 = len(f0.get("unlocked_quadrants", []))
            u1 = len(f1.get("unlocked_quadrants", []))

            # Unit counts
            w0 = len(f0.get("hands", [])) + 1
            w1 = len(f1.get("hands", [])) + 1

            cows0 = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("animal") == "COW")
            cows1 = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("animal") == "COW")

            straw0 = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            straw1 = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")

            melon0 = sum(1 for row in f0.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "MELON")
            melon1 = sum(1 for row in f1.get("tiles", []) for t in row if isinstance(t, dict) and t.get("crop") == "MELON")

            # Shed values
            priv0 = env.state[0].observation.private.get("shed", {})
            priv1 = env.state[1].observation.private.get("shed", {})

            entry = {
                "step": step,
                "day": step // 24,
                "m0": m0,
                "m1": m1,
                "delta": delta,
                "u0": u0,
                "u1": u1,
                "w0": w0,
                "w1": w1,
                "cows0": cows0,
                "cows1": cows1,
                "straw0": straw0,
                "straw1": straw1,
                "melon0": melon0,
                "melon1": melon1,
                "shed0": priv0,
                "shed1": priv1,
            }
            history.append(entry)

        step += 1

    print(f"{'Step':>5} | {'Day':>3} | {'Cand Money':>11} | {'Opp Money':>11} | {'Margin':>12} | {'Land':>5} | {'Workers':>7} | {'Cows':>5} | {'Straw':>5} | {'Melon':>5}")
    print("-" * 90)
    for h in history:
        print(f"{h['step']:5d} | {h['day']:3d} | ${h['m0']:10,.0f} | ${h['m1']:10,.0f} | ${h['delta']:+11,.0f} | {h['u0']}v{h['u1']:<2} | {h['w0']}v{h['w1']:<4} | {h['cows0']}v{h['cows1']:<2} | {h['straw0']}v{h['straw1']:<2} | {h['melon0']}v{h['melon1']:<2}")

    final_reward0 = float(env.state[0].reward or 0.0)
    final_reward1 = float(env.state[1].reward or 0.0)
    print("\n" + "=" * 90)
    print("WATERFALL MARGIN ATTRIBUTION AT TURN 720:")
    print("=" * 90)
    print(f"Final Candidate Wealth: ${final_reward0:,.2f}")
    print(f"Final Opponent Wealth : ${final_reward1:,.2f}")
    print(f"Total Economic Edge   : ${final_reward0 - final_reward1:+,.2f}")

    return history

if __name__ == "__main__":
    run_trajectory_attribution(42, bot_v83, "submission_v83")
    print("\n" + "#" * 90 + "\n")
    run_trajectory_attribution(42, bot_v18, "kaitofukami-v18")
