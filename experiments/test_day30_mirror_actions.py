"""EXP151 Forensic Diagnostic: Comparing Day 30 step-by-step labor actions and harvests."""
from __future__ import annotations
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def main():
    seed = 1000
    seat = 0
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = sub_d1.agent(obs0, env.configuration)
        try:
            a1 = opp_fn(obs1, env.configuration)
        except TypeError:
            a1 = opp_fn(obs1)

        if step >= 696:
            f0 = obs0.get("farms", [{}, {}])[0]
            f1 = obs0.get("farms", [{}, {}])[1]
            m0 = a0.get("market", []) if isinstance(a0, dict) else []
            m1 = a1.get("market", []) if isinstance(a1, dict) else []
            print(f"Step {step} (Hour {step%24:02d}):")
            print(f"  Hero Cash=${f0.get('money',0):.1f}, Shed={f0.get('inventory',{})} | Orders={m0}")
            print(f"  Opp  Cash=${f1.get('money',0):.1f}, Shed={f1.get('inventory',{})} | Orders={m1}")

        env.step([a0, a1] if seat == 0 else [a1, a0])

    print("\nFinal Result:")
    print(f"Hero Reward: ${env.state[0].reward} vs Opp Reward: ${env.state[1].reward}")

if __name__ == "__main__":
    main()
