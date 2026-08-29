"""EXP146 1-Seed Physical Proof: Validating Runway Thresholds & Cash Floors."""
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
from experiments.exp146_agents import agent_arm_a, agent_arm_b, agent_arm_c, agent_arm_d, agent_arm_e, agent_arm_f

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def run_proof_seed(seed: int = 1000):
    print("=" * 135)
    print(f"EXP146 1-SEED PHYSICAL PROOF ON SEED {seed}")
    print("=" * 135)

    arms = [
        ("Arm A: Control Baseline", agent_arm_a),
        ("Arm B: Runway >= 1.0 Day", agent_arm_b),
        ("Arm C: Runway >= 1.5 Days", agent_arm_c),
        ("Arm D: Runway >= 2.0 Days", agent_arm_d),
        ("Arm E: Runway >= 2.5 Days", agent_arm_e),
        ("Arm F: Runway >= 3.0 Days", agent_arm_f),
    ]

    for arm_name, ag_fn in arms:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        d10_cash = 0.0
        d15_cash = 0.0
        min_cash = 999999.0
        wheat_sold_early = 0
        wheat_sold_late = 0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            farms = obs0.get("farms", [{}, {}])
            f0 = farms[0]
            m0 = float(f0.get("money", 0))
            if m0 < min_cash:
                min_cash = m0

            if step == 240: d10_cash = m0
            elif step == 360: d15_cash = m0

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)

            if isinstance(a0, dict) and "market" in a0:
                for o in a0["market"]:
                    if len(o) >= 3 and o[0] == "SELL" and o[1] == "WHEAT":
                        if step < 600: wheat_sold_early += o[2]
                        else: wheat_sold_late += o[2]

            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        margin = r0 - r1
        won = (r0 > r1)

        print(f"  {arm_name:<28}: Reward=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${margin:+,.0f} | Won={won} | MinCash=${min_cash:,.0f} | D10=${d10_cash:,.0f} | D15=${d15_cash:,.0f} | WheatEarly={wheat_sold_early}")

if __name__ == "__main__":
    run_proof_seed(seed=1000)
    run_proof_seed(seed=42)
