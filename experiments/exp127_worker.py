"""EXP127 Chunk Worker: Evaluates 3 Arms (Control vs Price-Only vs Full Opponent-Conditioned) on 100 loss matches."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

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

def run_single_match(agent_d1_obj, seed: int, d1_seat: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    seat_0_is_d1 = (d1_seat == 0)

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        d1_obs = obs0 if seat_0_is_d1 else obs1
        opp_obs = obs1 if seat_0_is_d1 else obs0

        a_d1 = agent_d1_obj.act(d1_obs, env.configuration)
        try:
            a_opp = bot_v18_mod.agent(opp_obs, env.configuration)
        except TypeError:
            a_opp = bot_v18_mod.agent(opp_obs) if hasattr(bot_v18_mod, "agent") else bot_v18_mod(opp_obs)

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])

    r0 = float(env.state[d1_seat].reward or 0.0)
    r1 = float(env.state[1 - d1_seat].reward or 0.0)

    return {
        "reward": r0,
        "opp_reward": r1,
        "won": r0 > r1,
        "delta": r0 - r1,
        "pivoted": agent_d1_obj.pivots_done,
        "trigger_step": agent_d1_obj.trigger_step,
        "trigger_info": agent_d1_obj.trigger_details,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp127_worker.py <start_idx> <end_idx>")
        return

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    chunk = loss_cohort[start_idx:end_idx]
    results = []

    for i, match_info in enumerate(chunk, start=start_idx + 1):
        seed = match_info["seed"]
        seat = match_info["seat"]

        # Arm A: Control D.1 (+ Day 30 burst)
        agent_a = EXP127Agent(mode="CONTROL", day30_burst=True)
        res_a = run_single_match(agent_a, seed=seed, d1_seat=seat)

        # Arm B: Price-Only Adaptation (S2+S3)
        agent_b = EXP127Agent(mode="PRICE_ONLY", day30_burst=True)
        res_b = run_single_match(agent_b, seed=seed, d1_seat=seat)

        # Arm C: Full Opponent-Conditioned Adaptation (S1+S2+S3)
        agent_c = EXP127Agent(mode="FULL_OPPONENT", day30_burst=True)
        res_c = run_single_match(agent_c, seed=seed, d1_seat=seat)

        results.append({
            "match_id": i,
            "seed": seed,
            "seat": seat,
            "arm_a": res_a,
            "arm_b": res_b,
            "arm_c": res_c,
        })

    out_part = os.path.join(REPORTS_DIR, f"exp127_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
