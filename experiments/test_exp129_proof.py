"""EXP129 1-Seed Proof: Endgame Market Shock Defense Factorization.

Tests:
- Arm A: Control D.1 (+ Day 30 burst baseline)
- Arm B1: Milk-Price-Collapse Defense (Days 26-29: immediate milk shed liquidation upon collapse signal)
- Arm B2: Wheat/Feed-Spike Defense (Days 26-29: suppress late high-cost feed buys if wheat price spikes)
- Arm B3: Strawberry-Price-Collapse Defense (Days 26-29: immediate strawberry shed liquidation upon collapse signal)
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

class EXP129Agent:
    def __init__(self, mode: str = "CONTROL", day30_burst: bool = True):
        self.mode = mode  # "CONTROL", "B1_MILK", "B2_WHEAT", "B3_STRAW"
        self.day30_burst = day30_burst
        self.triggers_fired = 0
        self.trigger_details = []

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Endgame Shock Interventions on Days 26-29 (Steps 600-695)
        if self.mode != "CONTROL" and 600 <= step < 696:
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            p_milk = float(prices.get("MILK", 100.0) or 100.0)
            p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
            p_wheat = float(prices.get("WHEAT", 10.0) or 10.0)

            private_state = obs.get("private") or {}
            shed = private_state.get("shed", {}) or {}
            milk_in_shed = int(shed.get("MILK", 0) or 0)
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            # B1: Milk-Price-Collapse Defense
            if self.mode == "B1_MILK" and p_milk <= 95.0 and milk_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                    market_orders.append(["SELL", "MILK", milk_in_shed])
                    self.triggers_fired += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL MILK {milk_in_shed} @ ${p_milk:.1f}")

            # B2: Wheat/Feed-Spike Defense (Suppress late high-cost feed buys)
            elif self.mode == "B2_WHEAT" and p_wheat >= 12.0:
                new_orders = []
                for order in market_orders:
                    if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                        self.triggers_fired += 1
                        self.trigger_details.append(f"Day {day:02d} Step {step:03d}: CANCEL BUY WHEAT @ ${p_wheat:.1f}")
                    else:
                        new_orders.append(order)
                market_orders = new_orders

            # B3: Strawberry-Price-Collapse Defense
            elif self.mode == "B3_STRAW" and p_straw <= 125.0 and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    self.triggers_fired += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL STRAW {straw_in_shed} @ ${p_straw:.1f}")

        # Validated Day 30 Burst
        if self.day30_burst and day == 30 and hour == 0:
            slots = max(0, 10 - len(market_orders))
            for _ in range(min(6, slots)):
                market_orders.append(["HIRE"])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def test_single_seed(seed: int, seat: int = 0):
    print(f"\n--- Testing Seed {seed} (Seat {seat}) ---")
    for mode in ["CONTROL", "B1_MILK", "B2_WHEAT", "B3_STRAW"]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        agent_obj = EXP129Agent(mode=mode, day30_burst=True)

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            d1_obs = obs0 if seat == 0 else obs1
            opp_obs = obs1 if seat == 0 else obs0

            a_d1 = agent_obj.act(d1_obs, env.configuration)
            a_opp = bot_v18_mod.agent(opp_obs)

            a0 = a_d1 if seat == 0 else a_opp
            a1 = a_opp if seat == 0 else a_d1
            env.step([a0, a1])

        r0 = float(env.state[seat].reward or 0.0)
        r1 = float(env.state[1 - seat].reward or 0.0)
        delta = r0 - r1
        won = r0 > r1

        print(f"  [{mode:<10}]: D.1=${r0:,.0f} | Opp=${r1:,.0f} | Delta=${delta:+,.0f} | Won={won} | Triggers={agent_obj.triggers_fired} | Sample={agent_obj.trigger_details[:2]}")

def main():
    print("=" * 100)
    print("EXP129 1-SEED PROOF: ENDGAME MARKET SHOCK DEFENSE FACTORIZATION")
    print("=" * 100)
    test_single_seed(seed=1000, seat=0)
    test_single_seed(seed=1002, seat=0)
    test_single_seed(seed=42, seat=0)

if __name__ == "__main__":
    main()
