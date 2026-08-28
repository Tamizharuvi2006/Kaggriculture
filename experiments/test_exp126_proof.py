"""1-Seed Intervention Proof for EXP126 (Seed 42).

Compares:
- Arm A: Control D.1
- Arm B: D.1 + Midgame Accelerator (+2 HIRE on D20-26 when trapped yield >= 16)
- Arm C: D.1 + Day 30 Labor Burst (+6 HIRE on D30)
- Arm D: Combined (Arm B + Arm C)
"""
from __future__ import annotations
import os
import sys
import importlib.util

# Ensure UTF-8 on Windows
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

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

class EXP126Agent:
    def __init__(self, midgame_accel: bool = False, day30_burst: bool = False, min_trapped: int = 16, accel_hires: int = 2, day30_hires: int = 6):
        self.midgame_accel = midgame_accel
        self.day30_burst = day30_burst
        self.min_trapped = min_trapped
        self.accel_hires = accel_hires
        self.day30_hires = day30_hires
        self.triggers_fired = []
        self.total_extra_hires = 0

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Check Midgame Trigger (Days 20-26 Hour 0)
        if self.midgame_accel and 20 <= day <= 26 and hour == 0:
            player = int(obs.get("player", 0) or 0)
            farms = obs.get("farms", [])
            farm = farms[player] if len(farms) > player and isinstance(farms[player], dict) else {}
            trapped = sum(
                tile.get("yield_units", 0)
                for row in (farm.get("tiles") or [])
                for tile in (row if isinstance(row, list) else [row])
                if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY"
            )
            money = float(farm.get("money", 0.0) or 0.0)
            if trapped >= self.min_trapped and money >= 2000.0:
                slots = max(0, 10 - len(market_orders))
                to_add = min(self.accel_hires, slots)
                for _ in range(to_add):
                    market_orders.append(["HIRE"])
                    self.total_extra_hires += 1
                self.triggers_fired.append((day, step, trapped, to_add))

        # Check Day 30 Burst Trigger (Day 30 Hour 0)
        if self.day30_burst and day == 30 and hour == 0:
            slots = max(0, 10 - len(market_orders))
            to_add = min(self.day30_hires, slots)
            for _ in range(to_add):
                market_orders.append(["HIRE"])
                self.total_extra_hires += 1
            self.triggers_fired.append((day, step, 0, to_add))

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def test_arm(name: str, agent_obj, seed: int = 42):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        a0 = agent_obj.act(obs0, env.configuration)
        a1 = bot_v18_mod.agent(obs1)
        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    # Measure terminal stranded yield
    farm = env.state[0].observation.get("farms", [{}])[0]
    stranded = sum(
        tile.get("yield_units", 0)
        for row in (farm.get("tiles") or [])
        for tile in (row if isinstance(row, list) else [row])
        if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY"
    )

    print(f"\n[{name}]")
    print(f"  Final Reward     : ${r0:,.2f} vs Opponent ${r1:,.2f} | Delta = ${r0 - r1:+,.2f}")
    print(f"  Triggers Fired   : {agent_obj.triggers_fired}")
    print(f"  Total Extra Hires: {agent_obj.total_extra_hires}")
    print(f"  Terminal Stranded: {stranded} units")
    return r0, r1, stranded

def main():
    print("=" * 100)
    print("EXP126 1-SEED PROOF: MIDGAME ACCELERATOR vs DAY-30 BURST vs COMBINED (SEED 42)")
    print("=" * 100)

    # Arm A: Control D.1
    agent_a = EXP126Agent()
    r0_a, r1_a, s_a = test_arm("ARM A: Control D.1", agent_a)

    # Arm B: Midgame Accelerator
    agent_b = EXP126Agent(midgame_accel=True)
    r0_b, r1_b, s_b = test_arm("ARM B: Midgame Accelerator Only", agent_b)

    # Arm C: Day-30 Emergency Burst
    agent_c = EXP126Agent(day30_burst=True)
    r0_c, r1_c, s_c = test_arm("ARM C: Day-30 Emergency Burst Only", agent_c)

    # Arm D: Combined (Arm B + Arm C)
    agent_d = EXP126Agent(midgame_accel=True, day30_burst=True)
    r0_d, r1_d, s_d = test_arm("ARM D: Combined (Midgame + Day-30)", agent_d)

    print("\n" + "=" * 100)
    print("1-SEED FACTORIZATION COMPARISON:")
    print(f"  Arm A (Control) : ${r0_a:,.2f} (Baseline)")
    print(f"  Arm B (Midgame) : ${r0_b:,.2f} (${r0_b - r0_a:+,.2f})")
    print(f"  Arm C (Day 30)  : ${r0_c:,.2f} (${r0_c - r0_a:+,.2f})")
    print(f"  Arm D (Combined): ${r0_d:,.2f} (${r0_d - r0_a:+,.2f})")
    print("=" * 100)

if __name__ == "__main__":
    main()
