"""EXP167 Stage 1: Physical Proof of Fibonacci Hiring Cost on Day 29 (Step 696)."""
from __future__ import annotations
import os
import sys
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def test_stage1_fibonacci_hiring(seed: int = 1000):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    # Advance up to Step 695 (end of Day 28)
    while env.state[0].observation.get("step", 0) <= 695 and not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env.step([a0, a1])

    # Now we are at Step 696 (Day 29, Hour 0)
    obs0_696 = env.state[0].observation
    f0_696 = obs0_696.get("farms", [{}, {}])[0]
    cash_696 = float(f0_696.get("money", 0))
    hands_696 = len(f0_696.get("hands", []))
    hires_today_696 = f0_696.get("hires_today", 0)
    day_696 = obs0_696.get("day", 0)
    hour_696 = obs0_696.get("hour", 0)

    print(f"Step 696 State (Day {day_696}, Hour {hour_696}):")
    print(f"  Cash: ${cash_696:,.2f} | Hands Count: {hands_696} | Hires Today: {hires_today_696}")

    # Submit 10 HIRE orders at Step 696 (Hour 0 of Day 29)
    act0 = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"] for _ in range(10)]}
    obs1 = env.state[1].observation
    try: act1 = opp_fn(obs1, env.configuration)
    except TypeError: act1 = opp_fn(obs1)

    env.step([act0, act1])

    obs0_697 = env.state[0].observation
    f0_697 = obs0_697.get("farms", [{}, {}])[0]
    cash_697 = float(f0_697.get("money", 0))
    hands_697 = len(f0_697.get("hands", []))
    actual_cost = cash_696 - cash_697

    print(f"Step 697 State (After 10 Hires):")
    print(f"  Cash: ${cash_697:,.2f} | Hands Count: {hands_697} (Spawned: {hands_697 - hands_696})")
    print(f"  Actual Deducted Cost: ${actual_cost:.2f}")

    assert hands_697 == 10, f"Expected 10 hands, got {hands_697}"
    assert actual_cost == 143.0, f"Expected $143.00, got ${actual_cost}"
    print(f"  ✅ PHYSICAL PROOF VERIFIED: 10 workers spawned on Day 29 (Step 696) for exactly $143.00!")

if __name__ == "__main__":
    test_stage1_fibonacci_hiring()
