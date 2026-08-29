"""EXP137 1-Seed Physical Proof: Testing Arm A (Control) vs Arm B (Unconditional) vs Arm C (Adaptive Labor Gate)."""
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
from experiments.exp137_agents import agent_arm_a, agent_arm_b, agent_arm_c

# Load Benchmark Bot
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def run_proof_seed(seed: int = 1000):
    print("=" * 110)
    print(f"EXP137 1-SEED PROOF ON SEED {seed}")
    print("=" * 110)

    for arm_name, ag_fn in [("Arm A (Control Baseline)", agent_arm_a),
                            ("Arm B (Unconditional Labor)", agent_arm_b),
                            ("Arm C (Adaptive Labor Gate)", agent_arm_c)]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        step696_hires = 0
        step696_p_straw = 0.0
        step696_ripe = 0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            if step == 696:
                mkt = obs0.get("market", {}) or {}
                prices = mkt.get("prices", mkt.get("current_prices", {})) or {}
                step696_p_straw = float(prices.get("STRAWBERRY", 0))
                tiles = obs0.get("farms", [{}])[0].get("tiles", [])
                step696_ripe = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("stage") == 3)

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)

            if step == 696:
                step696_hires = sum(1 for m in a0.get("market", []) if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE")

            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        won = r0 > r1

        print(f"  {arm_name:<30}: D.1=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${r0-r1:+,.0f} | Won={won} | Step 696: P_Straw=${step696_p_straw:.1f}, Ripe={step696_ripe}, Hires={step696_hires}")

if __name__ == "__main__":
    run_proof_seed(seed=1000)
    run_proof_seed(seed=42)
    run_proof_seed(seed=20042)
