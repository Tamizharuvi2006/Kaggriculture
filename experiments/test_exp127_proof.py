"""EXP127 1-Seed Proof: Single-Slot Opponent-Conditioned Livestock Adaptation.

Compares:
- Arm A: Control D.1 (Unmodified baseline)
- Arm B: Price-Only Trigger (Wool >= $195 and Milk <= $130): Pivots 1 Cow -> 1 Sheep at first triggered animal buy step
- Arm C: Full Opponent-Conditioned Trigger (Opponent Sheep >= 1 and Wool >= $195 and Milk <= $130): Pivots 1 Cow -> 1 Sheep
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

class EXP127Agent:
    def __init__(self, mode: str = "CONTROL", wool_threshold: float = 195.0, milk_threshold: float = 130.0, day30_burst: bool = True):
        self.mode = mode  # "CONTROL", "PRICE_ONLY", "FULL_OPPONENT"
        self.wool_threshold = wool_threshold
        self.milk_threshold = milk_threshold
        self.day30_burst = day30_burst
        self.pivots_done = 0
        self.trigger_step = None
        self.trigger_details = None

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Check for single-slot Cow -> Sheep pivot on Days 5-12
        if self.mode != "CONTROL" and self.pivots_done == 0 and 5 <= day <= 12:
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            wool_p = float(prices.get("WOOL", 200.0) or 200.0)
            milk_p = float(prices.get("MILK", 160.0) or 160.0)

            # Signal S2 & S3
            price_condition = (wool_p >= self.wool_threshold and milk_p <= self.milk_threshold)

            # Signal S1: Opponent has sheep
            opp_sheep = 0
            player = int(obs.get("player", 0) or 0)
            farms = obs.get("farms", [])
            opp_farm = farms[1 - player] if len(farms) > (1 - player) and isinstance(farms[1 - player], dict) else {}
            for row in (opp_farm.get("tiles") or []):
                for tile in (row if isinstance(row, list) else [row]):
                    if isinstance(tile, dict) and tile.get("animal") == "SHEEP":
                        opp_sheep += 1

            opponent_condition = (opp_sheep >= 1)

            should_trigger = False
            if self.mode == "PRICE_ONLY" and price_condition:
                should_trigger = True
            elif self.mode == "FULL_OPPONENT" and price_condition and opponent_condition:
                should_trigger = True

            if should_trigger:
                # Intercept any ['BUY_ANIMAL', 'COW', qty] order and pivot 1 Cow -> 1 Sheep
                new_orders = []
                for order in market_orders:
                    if self.pivots_done == 0 and isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "BUY_ANIMAL" and order[1] == "COW":
                        new_orders.append(["BUY_ANIMAL", "SHEEP", 1])
                        self.pivots_done += 1
                        self.trigger_step = step
                        self.trigger_details = f"Day {day:02d} Step {step:03d}: Wool=${wool_p:.0f}, Milk=${milk_p:.0f}, OppSheep={opp_sheep}"
                    else:
                        new_orders.append(order)
                market_orders = new_orders

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
    for mode in ["CONTROL", "PRICE_ONLY", "FULL_OPPONENT"]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        agent_obj = EXP127Agent(mode=mode, day30_burst=True)

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

        print(f"  [{mode:<14}]: D.1=${r0:,.0f} | Opp=${r1:,.0f} | Delta=${delta:+,.0f} | Won={won} | Pivoted={agent_obj.pivots_done} | Info={agent_obj.trigger_details}")

def main():
    print("=" * 100)
    print("EXP127 1-SEED PROOF: SINGLE-SLOT ADAPTIVE LIVESTOCK RESPONSE")
    print("=" * 100)
    test_single_seed(seed=1000, seat=0)
    test_single_seed(seed=1002, seat=0)
    test_single_seed(seed=42, seat=0)

if __name__ == "__main__":
    main()
