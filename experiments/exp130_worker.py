"""EXP130 Chunk Worker: Evaluates 4 Arms (Control vs Arm B Milk vs Arm C Straw vs Arm D Combined) on 100 loss matches."""
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

class EXP130Agent:
    def __init__(self, mode: str = "A"):
        self.mode = mode  # "A" (Control+D30), "B" (+Milk), "C" (+Straw), "D" (+Both)
        self.milk_triggers = 0
        self.straw_triggers = 0
        self.trigger_details = []

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Check market prices and shed inventory on Days 26-29
        if self.mode in ["B", "C", "D"] and 600 <= step < 696:
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            p_milk = float(prices.get("MILK", 100.0) or 100.0)
            p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

            private_state = obs.get("private") or {}
            shed = private_state.get("shed", {}) or {}
            milk_in_shed = int(shed.get("MILK", 0) or 0)
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            # Milk-Collapse Defense (Arms B & D): Days 26-29, p_milk <= $95.0
            if self.mode in ["B", "D"] and p_milk <= 95.0 and milk_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                    market_orders.append(["SELL", "MILK", milk_in_shed])
                    self.milk_triggers += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL MILK {milk_in_shed} @ ${p_milk:.1f}")

            # Strawberry-Collapse Defense (Arms C & D): Days 27-29 (step >= 624), p_straw <= $125.0
            if self.mode in ["C", "D"] and step >= 624 and p_straw <= 125.0 and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    self.straw_triggers += 1
                    self.trigger_details.append(f"Day {day:02d} Step {step:03d}: SELL STRAW {straw_in_shed} @ ${p_straw:.1f}")

        # Validated Day 30 Labor Burst (Arms A, B, C, D)
        if day == 30 and hour == 0:
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
        "milk_triggers": agent_d1_obj.milk_triggers,
        "straw_triggers": agent_d1_obj.straw_triggers,
        "sample_trigger": agent_d1_obj.trigger_details[0] if agent_d1_obj.trigger_details else None,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp130_worker.py <start_idx> <end_idx>")
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

        # Arm A: Control Baseline (D.1 + Day 30 burst)
        agent_a = EXP130Agent(mode="A")
        res_a = run_single_match(agent_a, seed=seed, d1_seat=seat)

        # Arm B: Milk Price Collapse Defense
        agent_b = EXP130Agent(mode="B")
        res_b = run_single_match(agent_b, seed=seed, d1_seat=seat)

        # Arm C: Strawberry Collapse Defense
        agent_c = EXP130Agent(mode="C")
        res_c = run_single_match(agent_c, seed=seed, d1_seat=seat)

        # Arm D: Combined Policy (Milk + Strawberry)
        agent_d = EXP130Agent(mode="D")
        res_d = run_single_match(agent_d, seed=seed, d1_seat=seat)

        results.append({
            "match_id": i,
            "seed": seed,
            "seat": seat,
            "arm_a": res_a,
            "arm_b": res_b,
            "arm_c": res_c,
            "arm_d": res_d,
        })

    out_part = os.path.join(REPORTS_DIR, f"exp130_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
