"""EXP128 Chunk Worker: Step-by-Step Opponent Action-Causality Forensics across 100 Loss Matches."""
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

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

def _calc_farm_wealth(farm, prices, shed=None):
    if not isinstance(farm, dict):
        return 0.0, 0, 0
    money = float(farm.get("money", 0.0) or 0.0)
    cows = 0
    sheep = 0
    land = len(farm.get("unlocked_quadrants", []) or [])
    for row in (farm.get("tiles") or []):
        for tile in (row if isinstance(row, list) else [row]):
            if isinstance(tile, dict):
                if tile.get("animal") == "COW": cows += 1
                elif tile.get("animal") == "SHEEP": sheep += 1

    inv_val = 0.0
    if isinstance(shed, dict):
        for p, q in shed.items():
            inv_val += float(q or 0.0) * float(prices.get(p, 1.0) or 1.0)

    wealth = money + inv_val + cows * 400.0 + sheep * 500.0 + max(0, land - 1) * 1000.0
    return wealth, cows, sheep

def analyze_match_causality(seed: int, d1_seat: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    seat_0_is_d1 = (d1_seat == 0)

    step_records = []
    prev_prices = {}

    step = 0
    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        d1_obs = obs0 if seat_0_is_d1 else obs1
        opp_obs = obs1 if seat_0_is_d1 else obs0

        farms = d1_obs.get("farms", [])
        d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
        opp_farm = farms[1 - d1_seat] if len(farms) > (1 - d1_seat) else {}

        market = d1_obs.get("market", {}) or {}
        prices = {p: float(prices_dict.get(p, 1.0) or 1.0) for p in PRODUCTS} if isinstance(prices_dict := market.get("prices", market.get("current_prices", {})), dict) else {}

        d1_shed = (d1_obs.get("private") or {}).get("shed", {})

        d1_wealth, d1_cows, d1_sheep = _calc_farm_wealth(d1_farm, prices, d1_shed)
        opp_wealth, opp_cows, opp_sheep = _calc_farm_wealth(opp_farm, prices, None)

        d1_money = float(d1_farm.get("money", 0.0) or 0.0)
        opp_money = float(opp_farm.get("money", 0.0) or 0.0)

        # Get Actions
        a_d1 = sub_d1.agent(d1_obs, env.configuration)
        try:
            a_opp = bot_v18_mod.agent(opp_obs, env.configuration)
        except TypeError:
            a_opp = bot_v18_mod.agent(opp_obs) if hasattr(bot_v18_mod, "agent") else bot_v18_mod(opp_obs)

        # Parse Opponent Market Orders
        opp_orders = list(a_opp.get("market") or [])
        opp_sells = []
        opp_buys = []
        opp_hires = 0
        opp_land = 0
        opp_animals = []

        for o in opp_orders:
            if not isinstance(o, (list, tuple)) or len(o) == 0:
                continue
            otype = o[0]
            if otype == "SELL" and len(o) >= 3:
                opp_sells.append({"item": o[1], "qty": int(o[2])})
            elif otype == "BUY_PRODUCT" and len(o) >= 3:
                opp_buys.append({"item": o[1], "qty": int(o[2])})
            elif otype == "HIRE":
                opp_hires += 1
            elif otype == "BUY_LAND":
                opp_land += 1
            elif otype == "BUY_ANIMAL" and len(o) >= 2:
                opp_animals.append(o[1])

        # Track Price Movements from previous step
        price_deltas = {}
        if prev_prices:
            for p in PRODUCTS:
                price_deltas[p] = prices.get(p, 1.0) - prev_prices.get(p, 1.0)
        prev_prices = prices.copy()

        step_records.append({
            "step": step,
            "day": (step // 24) + 1,
            "hour": step % 24,
            "d1_money": d1_money,
            "opp_money": opp_money,
            "money_deficit": opp_money - d1_money,
            "d1_wealth": d1_wealth,
            "opp_wealth": opp_wealth,
            "wealth_deficit": opp_wealth - d1_wealth,
            "d1_cows": d1_cows,
            "opp_cows": opp_cows,
            "d1_sheep": d1_sheep,
            "opp_sheep": opp_sheep,
            "opp_land": len(opp_farm.get("unlocked_quadrants", []) or []),
            "d1_land": len(d1_farm.get("unlocked_quadrants", []) or []),
            "opp_sells": opp_sells,
            "opp_buys": opp_buys,
            "opp_hires": opp_hires,
            "opp_land_buys": opp_land,
            "opp_animals": opp_animals,
            "prices": prices,
            "price_deltas": price_deltas,
        })

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])
        step += 1

    final_r0 = float(env.state[d1_seat].reward or 0.0)
    final_r1 = float(env.state[1 - d1_seat].reward or 0.0)
    final_delta = final_r0 - final_r1

    # Find the Point of No Return: First Persistent Deficit Step (T_deficit)
    # Defined as the first step after which Wealth Deficit > 0 for all remaining steps, or after which D.1 never leads again
    t_persistent_deficit = 719
    for i in range(len(step_records)):
        # Check if opp_wealth >= d1_wealth for all steps from i to end
        rem_deficits = [r["wealth_deficit"] for r in step_records[i:]]
        if all(d >= 0 for d in rem_deficits):
            t_persistent_deficit = i
            break

    # Analyze Precursor Window [max(0, T_deficit - 24) to T_deficit]
    precursor_window = step_records[max(0, t_persistent_deficit - 24): t_persistent_deficit + 1]

    # Classify the Primary Divergence Driver
    divergence_category = "UNKNOWN"
    primary_event_info = {}

    # Check 1: Early Livestock Disparity
    rec_at_div = step_records[t_persistent_deficit]
    day_div = rec_at_div["day"]

    # Check for early milk/wool price shocks in precursor window
    milk_shocks = [r for r in precursor_window if r.get("price_deltas", {}).get("MILK", 0) < -10]
    straw_shocks = [r for r in precursor_window if r.get("price_deltas", {}).get("STRAWBERRY", 0) < -10]
    opp_big_sells = [r for r in precursor_window if any(s["qty"] >= 5 for s in r["opp_sells"])]

    if day_div <= 12 and rec_at_div["opp_cows"] + rec_at_div["opp_sheep"] > rec_at_div["d1_cows"] + rec_at_div["d1_sheep"]:
        divergence_category = "OPP_EARLY_LIVESTOCK_SURGE"
        primary_event_info = {
            "opp_cows": rec_at_div["opp_cows"],
            "opp_sheep": rec_at_div["opp_sheep"],
            "d1_cows": rec_at_div["d1_cows"],
            "d1_sheep": rec_at_div["d1_sheep"],
        }
    elif day_div <= 10 and rec_at_div["opp_land"] > rec_at_div["d1_land"]:
        divergence_category = "OPP_LAND_EXPANSION_TEMPO"
        primary_event_info = {"opp_land": rec_at_div["opp_land"], "d1_land": rec_at_div["d1_land"]}
    elif milk_shocks and opp_big_sells:
        divergence_category = "OPP_MILK_PRICE_COLLAPSE"
        primary_event_info = {"shocks": len(milk_shocks), "sells": len(opp_big_sells)}
    elif straw_shocks and opp_big_sells:
        divergence_category = "OPP_STRAWBERRY_PRICE_COLLAPSE"
        primary_event_info = {"shocks": len(straw_shocks), "sells": len(opp_big_sells)}
    elif any(r["opp_buys"] for r in precursor_window):
        divergence_category = "OPP_FEED_MARKET_PRESSURE"
        primary_event_info = {"buys": sum(len(r["opp_buys"]) for r in precursor_window)}
    elif day_div <= 18:
        divergence_category = "MIDGAME_LIQUIDITY_COMPOUNDING"
        primary_event_info = {"deficit_at_div": rec_at_div["wealth_deficit"]}
    else:
        divergence_category = "LATE_GAME_HARVEST_DEFICIT"
        primary_event_info = {"deficit_at_div": rec_at_div["wealth_deficit"]}

    return {
        "seed": seed,
        "seat": d1_seat,
        "final_d1": final_r0,
        "final_opp": final_r1,
        "final_delta": final_delta,
        "t_persistent_deficit": t_persistent_deficit,
        "day_persistent_deficit": day_div,
        "divergence_category": divergence_category,
        "primary_event_info": primary_event_info,
        "deficit_at_point_of_no_return": rec_at_div["wealth_deficit"],
        "milk_price_at_point_of_no_return": rec_at_div["prices"].get("MILK", 0),
        "wool_price_at_point_of_no_return": rec_at_div["prices"].get("WOOL", 0),
        "straw_price_at_point_of_no_return": rec_at_div["prices"].get("STRAWBERRY", 0),
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp128_action_causality_worker.py <start_idx> <end_idx>")
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
        causality_report = analyze_match_causality(seed, seat)
        causality_report["match_id"] = i
        results.append(causality_report)

    out_part = os.path.join(REPORTS_DIR, f"exp128_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
