"""EXP141 1-Seed Physical Instrumentation Proof: Validating CARE Mechanism at the Environment Level."""
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

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def agent_control(obs, config=None):
    """Arm A: Pure D.1 Baseline Control."""
    return sub_d1.agent(obs, config)

def make_care_agent(target_animal: str = "ALL"):
    """Creates a CARE-enabled agent for target_animal ('COW', 'SHEEP', or 'ALL')."""
    def care_agent(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = (step // 24) + 1
        act = sub_d1.agent(obs, config)

        if 6 <= day <= 10:
            player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
            farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
            own_f = farms[player] if len(farms) > player else {}
            pos = own_f.get("farmer", [0, 0])
            y, x = pos
            tiles = own_f.get("tiles", []) or []
            if y < len(tiles) and x < len(tiles[0]):
                t = tiles[y][x]
                if isinstance(t, dict) and "animal" in t:
                    an = t.get("animal")
                    cared = t.get("cared_today", False)
                    if not cared:
                        if target_animal == "ALL" or target_animal == an:
                            act["farmer"] = ["CARE"]
        return act
    return care_agent

def run_instrumentation_proof(seed: int = 1000):
    print("=" * 125)
    print(f"EXP141 1-SEED PHYSICAL INSTRUMENTATION PROOF ON SEED {seed}")
    print("=" * 125)

    arms = [
        ("Arm A: Pure D.1 Control", agent_control),
        ("Arm B: Early CARE (Cows Only)", make_care_agent("COW")),
        ("Arm C: Early CARE (Sheep Only)", make_care_agent("SHEEP")),
        ("Arm D: Early CARE (All Livestock)", make_care_agent("ALL")),
    ]

    results = []

    for arm_name, ag_fn in arms:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        care_count = 0
        max_care_bonus = 0
        total_milk_harvested = 0
        total_wool_harvested = 0
        d10_money = 0.0
        d15_money = 0.0
        d20_money = 0.0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            farms = obs0.get("farms", [{}, {}])
            f0 = farms[0]

            # Track animal state on own farm
            tiles0 = f0.get("tiles", [])
            for r in tiles0:
                for t in r:
                    if isinstance(t, dict) and "animal" in t:
                        b = t.get("pending_care_bonus", 0) or 0
                        if b > max_care_bonus:
                            max_care_bonus = b

            if step == 240:  # Day 10
                d10_money = float(f0.get("money", 0))
            elif step == 360:  # Day 15
                d15_money = float(f0.get("money", 0))
            elif step == 480:  # Day 20
                d20_money = float(f0.get("money", 0))

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)

            if isinstance(a0, dict) and a0.get("farmer") == ["CARE"]:
                care_count += 1

            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        won = (r0 > r1)
        margin = r0 - r1

        results.append({
            "arm": arm_name,
            "reward_hero": r0,
            "reward_opp": r1,
            "margin": margin,
            "won": won,
            "care_actions": care_count,
            "max_care_bonus": max_care_bonus,
            "d10_money": d10_money,
            "d15_money": d15_money,
            "d20_money": d20_money,
        })

        print(f"  {arm_name:<35}: Reward=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${margin:+,.0f} | Won={won} | CAREs={care_count} | Max Bonus={max_care_bonus} | D10=${d10_money:,.0f} | D15=${d15_money:,.0f}")

    return results

if __name__ == "__main__":
    run_instrumentation_proof(seed=1000)
    run_instrumentation_proof(seed=42)
    run_instrumentation_proof(seed=20042)
