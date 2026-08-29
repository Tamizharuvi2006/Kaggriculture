"""EXP139 Physical Trigger Proof: Verify Arm A vs Arm B vs Arm C on representative seeds."""
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
from experiments.exp139_agents import agent_arm_a, agent_arm_b, agent_arm_c

# Load Benchmark Bot
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def run_proof_seed(seed: int = 1000):
    print("=" * 110)
    print(f"EXP139 TRIGGER PROOF ON SEED {seed}")
    print("=" * 110)

    for arm_name, ag_fn in [("Arm A (Control Baseline)", agent_arm_a),
                            ("Arm B (Adaptive Livestock)", agent_arm_b),
                            ("Arm C (Adaptive Market Liquidity)", agent_arm_c)]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        d15_c0 = 0.0
        d15_c1 = 0.0
        d20_c0 = 0.0
        d20_c1 = 0.0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            if step == 360:  # Day 15
                d15_c0 = float(obs0.get("farms", [{}])[0].get("money", 0))
                d15_c1 = float(obs1.get("farms", [{}])[1].get("money", 0))
            elif step == 480:  # Day 20
                d20_c0 = float(obs0.get("farms", [{}])[0].get("money", 0))
                d20_c1 = float(obs1.get("farms", [{}])[1].get("money", 0))

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)
            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        won = r0 > r1

        print(f"  {arm_name:<35}: D.1=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${r0-r1:+,.0f} | Won={won} | D15 Margin=${d15_c0-d15_c1:+,.0f} | D20 Margin=${d20_c0-d20_c1:+,.0f}")

if __name__ == "__main__":
    run_proof_seed(seed=1000)
    run_proof_seed(seed=42)
    run_proof_seed(seed=20042)
