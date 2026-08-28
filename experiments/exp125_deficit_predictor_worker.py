"""EXP125 Chunk Worker: Extracts checkpoint telemetry across Days 5, 10, 15, 20, 25, 27, 29."""
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

CHECKPOINTS = [5, 10, 15, 20, 25, 27, 29]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

def _extract_farm_metrics(farm, prices, shed=None):
    if not isinstance(farm, dict):
        return {
            "money": 0.0,
            "cows": 0,
            "sheep": 0,
            "plants": 0,
            "strawberries": 0,
            "wheat": 0,
            "hands": 0,
            "land": 0,
            "ripe_strawberries": 0,
            "unharvested_yield": 0,
            "inventory_value": 0.0,
            "total_estimated_wealth": 0.0,
        }

    money = float(farm.get("money", 0.0) or 0.0)
    hands = len(farm.get("hands", []) or [])
    land = len(farm.get("unlocked_quadrants", []) or [])

    cows = 0
    sheep = 0
    plants = 0
    strawberries = 0
    wheat = 0
    ripe_strawberries = 0
    unharvested_yield = 0

    for row in (farm.get("tiles") or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            crop = tile.get("crop")
            animal = tile.get("animal")
            yield_units = tile.get("yield_units", 0) or 0

            if animal == "COW":
                cows += 1
            elif animal == "SHEEP":
                sheep += 1

            if kind == "PLANT":
                plants += 1
                if crop == "STRAWBERRY":
                    strawberries += 1
                    if yield_units > 0:
                        ripe_strawberries += 1
                        unharvested_yield += yield_units
                elif crop == "WHEAT":
                    wheat += 1

    inv_value = 0.0
    if isinstance(shed, dict):
        for prod, qty in shed.items():
            price = float(prices.get(prod, 1.0) or 1.0)
            inv_value += float(qty or 0.0) * price

    # Total wealth estimate = liquid cash + shed goods + animal book value ($400/cow, $500/sheep) + land value ($1000/quadrant)
    animal_asset_val = cows * 400.0 + sheep * 500.0
    land_asset_val = max(0, land - 1) * 1000.0
    total_wealth = money + inv_value + animal_asset_val + land_asset_val

    return {
        "money": money,
        "cows": cows,
        "sheep": sheep,
        "plants": plants,
        "strawberries": strawberries,
        "wheat": wheat,
        "hands": hands,
        "land": land,
        "ripe_strawberries": ripe_strawberries,
        "unharvested_yield": unharvested_yield,
        "inventory_value": inv_value,
        "total_estimated_wealth": total_wealth,
    }

def run_match_telemetry(seed: int, d1_seat: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    seat_0_is_d1 = (d1_seat == 0)

    checkpoint_steps = {(day - 1) * 24: day for day in CHECKPOINTS}
    telemetry = {}

    step_idx = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        if step_idx in checkpoint_steps:
            day = checkpoint_steps[step_idx]
            d1_obs = obs0 if seat_0_is_d1 else obs1
            opp_obs = obs1 if seat_0_is_d1 else obs0

            farms = d1_obs.get("farms", [])
            d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
            opp_farm = farms[1 - d1_seat] if len(farms) > (1 - d1_seat) else {}

            market = d1_obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}

            d1_shed = (d1_obs.get("private") or {}).get("shed", {})

            d1_metrics = _extract_farm_metrics(d1_farm, prices, d1_shed)
            opp_metrics = _extract_farm_metrics(opp_farm, prices, None)

            telemetry[f"day_{day}"] = {
                "day": day,
                "step": step_idx,
                "d1_metrics": d1_metrics,
                "opp_metrics": opp_metrics,
                "prices": {p: float(prices.get(p, 0.0) or 0.0) for p in PRODUCTS},
                "wealth_deficit": opp_metrics["total_estimated_wealth"] - d1_metrics["total_estimated_wealth"],
                "money_deficit": opp_metrics["money"] - d1_metrics["money"],
                "cow_deficit": opp_metrics["cows"] - d1_metrics["cows"],
                "sheep_deficit": opp_metrics["sheep"] - d1_metrics["sheep"],
                "milk_price": float(prices.get("MILK", 0.0) or 0.0),
                "wool_price": float(prices.get("WOOL", 0.0) or 0.0),
                "straw_price": float(prices.get("STRAWBERRY", 0.0) or 0.0),
                "wheat_price": float(prices.get("WHEAT", 0.0) or 0.0),
            }

        # Step Environment
        d1_obs_act = obs0 if seat_0_is_d1 else obs1
        opp_obs_act = obs1 if seat_0_is_d1 else obs0

        a_d1 = sub_d1.agent(d1_obs_act, env.configuration)
        try:
            a_opp = bot_v18_mod.agent(opp_obs_act, env.configuration)
        except TypeError:
            a_opp = bot_v18_mod.agent(opp_obs_act) if hasattr(bot_v18_mod, "agent") else bot_v18_mod(opp_obs_act)

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])
        step_idx += 1

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    d1_rew = r0 if seat_0_is_d1 else r1
    opp_rew = r1 if seat_0_is_d1 else r0

    return {
        "d1_final_reward": d1_rew,
        "opp_final_reward": opp_rew,
        "final_delta": d1_rew - opp_rew,
        "checkpoints": telemetry,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp125_deficit_predictor_worker.py <start_idx> <end_idx>")
        return

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])

    loss_file = os.path.join(REPORTS_DIR, "exp124_day30_labor_burst_results.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        matches = json.load(f)

    chunk = matches[start_idx:end_idx]
    results = []

    for item in chunk:
        seed = item["seed"]
        seat = item["seat"]
        match_id = item["match_id"]
        transition = item["transition"]
        rew_delta = item["reward_delta"]

        # Assign EXP124 Cohort Category
        if transition == "LOSS_TO_WIN":
            cohort = "CONVERTED"
        elif rew_delta > 0:
            cohort = "UNCONVERTED_POSITIVE"
        else:
            cohort = "UNAFFECTED"

        match_telemetry = run_match_telemetry(seed, seat)
        results.append({
            "match_id": match_id,
            "seed": seed,
            "seat": seat,
            "cohort": cohort,
            "exp124_delta": rew_delta,
            "arm_a_d1_rew": item["arm_a_reward"],
            "arm_a_opp_rew": item["arm_a_opp_reward"],
            "telemetry": match_telemetry,
        })

    out_part = os.path.join(REPORTS_DIR, f"exp125_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
