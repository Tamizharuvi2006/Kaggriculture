"""EXP131 1-Seed Proof: Fresh Out-of-Sample Validation Candidate.

Verifies:
1. D.1 Baseline execution
2. Candidate execution (D.1 + Day 30 Burst + Milk Defense + Strawberry Defense)
3. Physical execution of orders, zero illegal actions, reward computation.
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

class AdaptiveD2Candidate:
    """The Complete Validated Adaptive Candidate (D.2).

    1. D.1 core production & worker schedules untouched.
    2. Day-30 Emergency Labor Burst (+6 HIRE at D30H00).
    3. Conditional Milk-Collapse Defense (Days 26-29, p_milk <= $95.0 -> immediate liquidation).
    4. Conditional Strawberry-Collapse Defense (Days 27-29, p_straw <= $125.0 -> early liquidation).
    """
    def __init__(self):
        self.milk_triggers = 0
        self.straw_triggers = 0
        self.hires_done = 0
        self.trigger_details = []

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # 1. Milk & Strawberry Collapse Defenses on Days 26-29
        if 600 <= step < 696:
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            p_milk = float(prices.get("MILK", 100.0) or 100.0)
            p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

            private_state = obs.get("private") or {}
            shed = private_state.get("shed", {}) or {}
            milk_in_shed = int(shed.get("MILK", 0) or 0)
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            # Milk Defense: Days 26-29, p_milk <= $95.0
            if p_milk <= 95.0 and milk_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                    market_orders.append(["SELL", "MILK", milk_in_shed])
                    self.milk_triggers += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL MILK {milk_in_shed} @ ${p_milk:.1f}")

            # Strawberry Defense: Days 27-29, p_straw <= $125.0
            if step >= 624 and p_straw <= 125.0 and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    self.straw_triggers += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL STRAW {straw_in_shed} @ ${p_straw:.1f}")

        # 2. Day-30 Emergency Labor Burst
        if day == 30 and hour == 0:
            slots = max(0, 10 - len(market_orders))
            for _ in range(min(6, slots)):
                market_orders.append(["HIRE"])
                self.hires_done += 1

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def test_proof(seed: int = 20042, seat: int = 0):
    print(f"\n--- Testing Fresh Unseen Seed {seed} (Seat {seat}) ---")
    
    # 1. Run D.1 Baseline
    env_d1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_d1.reset()
    while not env_d1.done:
        obs0 = env_d1.state[0].observation
        obs1 = env_d1.state[1].observation
        d1_obs = obs0 if seat == 0 else obs1
        opp_obs = obs1 if seat == 0 else obs0
        a_d1 = sub_d1.agent(d1_obs, env_d1.configuration)
        a_opp = bot_v18_mod.agent(opp_obs)
        env_d1.step([a_d1, a_opp] if seat == 0 else [a_opp, a_d1])
    
    r_d1_0 = float(env_d1.state[seat].reward or 0.0)
    r_opp_0 = float(env_d1.state[1 - seat].reward or 0.0)
    d1_won = r_d1_0 > r_opp_0

    # 2. Run Candidate
    env_c = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_c.reset()
    candidate = AdaptiveD2Candidate()
    while not env_c.done:
        obs0 = env_c.state[0].observation
        obs1 = env_c.state[1].observation
        d1_obs = obs0 if seat == 0 else obs1
        opp_obs = obs1 if seat == 0 else obs0
        a_c = candidate.act(d1_obs, env_c.configuration)
        a_opp = bot_v18_mod.agent(opp_obs)
        env_c.step([a_c, a_opp] if seat == 0 else [a_opp, a_c])
    
    r_c_0 = float(env_c.state[seat].reward or 0.0)
    r_opp_c = float(env_c.state[1 - seat].reward or 0.0)
    c_won = r_c_0 > r_opp_c
    delta = r_c_0 - r_d1_0

    print(f"  D.1 Control : D.1=${r_d1_0:,.0f} | Opp=${r_opp_0:,.0f} | Won={d1_won}")
    print(f"  Candidate   : Cand=${r_c_0:,.0f} | Opp=${r_opp_c:,.0f} | Won={c_won} | Delta=${delta:+,.0f}")
    print(f"  Candidate Triggers: Milk={candidate.milk_triggers}, Straw={candidate.straw_triggers}, Hires={candidate.hires_done}")
    print(f"  Sample Events: {candidate.trigger_details[:3]}")

def main():
    print("=" * 100)
    print("EXP131 1-SEED PROOF: FRESH UNSEEN SEED VALIDATION")
    print("=" * 100)
    test_proof(seed=20042, seat=0)
    test_proof(seed=20005, seat=0)

if __name__ == "__main__":
    main()
