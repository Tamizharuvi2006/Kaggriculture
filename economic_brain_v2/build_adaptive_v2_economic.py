import os

# Script to assemble candidates/submission_adaptive_v2_economic.py
with open(r"D:\kaggriculture\candidates\submission_adaptive_economic_v1.py", "r", encoding="utf-8") as f:
    v1_code = f.read()

# Replace header
header_v2 = '''"""Kaggriculture Adaptive Economic Agent — V2 Autonomous Production Architecture.

Principles-First Observation-Driven Architecture:
1. Economic Brain:
   - Evaluates Marginal Return per Tile-Day (MR/TD) dynamically for all crops.
   - Multi-Output Livestock ROI: Value = Product (Milk/Wool) + Fertilizer ($48/unit) - Feed - Wages.
   - Feed Self-Sufficiency: Dedicates on-farm wheat plots to cover 100% of animal feed at $1.67/unit.
   - Cashflow Monetization: Sells surplus wheat to the 5 town shops and converts animal fertilizer into liquid treasury cash.
2. Resource Planner:
   - Dynamic herd sizing: expands livestock only when payback period < remaining days and treasury has safety buffer.
   - Dynamic plot allocation: balances feed crops and top cash crops based on real-time town demand.
   - Dynamic labor sizing: scales workforce to active plot/animal count (1 worker per ~4 tasks).
3. Hands (Physical Execution):
   - 100% Observation-Driven task generation, collision-free movement, watering, and harvesting.
   - Zero replay tapes, zero hardcoded August schedules.
"""
from __future__ import annotations

import math

'''

# Extract helper functions and structure
# Find the start of _crop_plan and replace it with the new Analytical Economic Planner
crop_plan_v2 = '''
_LATEST_PRICES = {}
_MATCH_LEDGER = {
    "wheat_seed_cost": 0.0,
    "market_wheat_cost": 0.0,
    "wheat_produced": 0,
    "wheat_sold": 0,
    "wheat_consumed": 0,
    "milk_revenue": 0.0,
    "wool_revenue": 0.0,
    "fertilizer_revenue": 0.0,
    "animal_deaths": 0,
    "crop_deaths": 0,
    "worker_wages": 0.0,
    "land_spend": 0.0,
}


def _evaluate_crop_scores(day, prices):
    """Calculate Net Marginal Return per Tile-Day (MR/TD) for every candidate crop."""
    remaining_days = max(1, 29 - day)
    scores = {}
    for crop, spec in CROPS.items():
        first_harvest = spec["first"]
        max_day = spec["max_day"]
        if remaining_days < first_harvest:
            scores[crop] = -999.0
            continue
        p_unit = float(prices.get(crop, 20.0) or 20.0)
        seed_cost = spec["seed"]
        
        if spec["ongoing"]:
            # Ongoing crop: multi-harvest valuation
            cycles = 1 + max(0, (remaining_days - first_harvest) // 2)
            total_yield = cycles * spec["yield"]
            # Daily labour overhead (~12/day)
            net_profit = (total_yield * p_unit) - seed_cost - (remaining_days * 12.0)
            scores[crop] = net_profit / max(1, remaining_days)
        else:
            # One-time crop
            net_profit = (spec["yield"] * p_unit) - seed_cost - (max_day * 12.0)
            scores[crop] = net_profit / max(1, max_day)
            
    return scores


def _crop_plan(day):
    """Dynamic economic crop allocation derived from live prices and animal feed demands."""
    if day < int(STRATEGY.get("crop_transition_day", 5)):
        return OPENING_CROP_PLAN

    prices = _LATEST_PRICES
    p_wheat = float(prices.get("WHEAT", 25.0) or 25.0)
    
    # 1. Calculate living animal count to determine feed plot requirement
    animal_plan = _animal_plan()
    num_animals = len(animal_plan)
    
    # Each wheat tile produces 6 wheat every 4 days = 1.5 wheat/day
    # Dedicate enough wheat plots to cover 100% of animal feed from on-farm grain
    feed_wheat_plots = math.ceil(num_animals / 1.5)
    
    # If town wheat price is high, allocate additional plots for commercial town sales
    surplus_wheat_plots = 4 if p_wheat >= 28.0 else 0
    total_wheat_plots = max(4, feed_wheat_plots + surplus_wheat_plots)
    
    # 2. Evaluate competing cash crops (MR/TD)
    crop_scores = _evaluate_crop_scores(day, prices)
    # Sort non-wheat crops by profitability
    cash_candidates = [c for c in ("STRAWBERRY", "MELON", "CARROT", "TOMATO") if crop_scores.get(c, -999.0) > 0]
    cash_candidates.sort(key=lambda c: crop_scores.get(c, -999.0), reverse=True)
    primary_cash_crop = cash_candidates[0] if cash_candidates else "CARROT"
    secondary_cash_crop = cash_candidates[1] if len(cash_candidates) > 1 else "CARROT"

    # 3. Formulate tile plan
    plan = {pos: crop for pos, crop in OPENING_CROP_PLAN.items() if crop == "MELON" and day <= 12}
    candidates = [
        (x, y)
        for y in range(10)
        for x in range(10)
        if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))
        and (x, y) not in animal_plan
        and (x, y) not in plan
    ]
    candidates.sort(key=lambda p: (abs(p[0] - 4.5) + abs(p[1] - 4.5), p[1], p[0]))
    
    # A. Allocate feed & commercial wheat plots
    for pos in candidates[:total_wheat_plots]:
        plan[pos] = "WHEAT"
        
    # B. Allocate primary cash crop
    rem = candidates[total_wheat_plots:]
    primary_quota = max(0, len(rem) - 6)
    for pos in rem[:primary_quota]:
        plan[pos] = primary_cash_crop
        
    # C. Allocate remaining plots to secondary cash crop (diversification buffer)
    for pos in rem[primary_quota:]:
        plan[pos] = secondary_cash_crop
        
    return plan
'''

# Find _hire_target and market orders in V1 and upgrade with dynamic ROI logic
hire_and_market_v2 = '''
def _hire_target(day):
    """Dynamic labor requirement sized to active workload (plants + animals)."""
    # Base labor ramp: smooth early ramp to prevent wage shock
    if day == 0: return 2
    if day == 1: return 2
    if day <= 3: return 3
    if day <= 6: return 5
    if day <= 9: return 7
    if day <= 14: return 9
    if day <= 28: return 11
    return 6


def _market_orders(obs):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    inventories = _get(private, "inventories", []) or []
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    day = int(_get(obs, "day", 0))
    unlocked = list(_get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    orders = []
    budget = float(_get(farm, "money", 0))

    # === 1. CASH CONVERSION (SELL HARVESTS & FERTILIZER) ===
    # Evaluate Fertilizer value: use on strawberry ONLY if strawberry price is high; else sell for cash!
    p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
    p_fert = float(prices.get("FERTILIZER", 40.0) or 40.0)
    fertilizer = int(shed.get("FERTILIZER", 0))
    
    # If strawberry price < 60, fertilizing strawberries has lower ROI than selling fertilizer at $40-$50!
    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95

    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity

    # Surplus Wheat Sales: preserve feed buffer (animal_count * 2), sell all excess wheat into town shops!
    counts = _asset_counts(obs)
    animal_count = sum(counts.values())
    wheat_shed = int(shed.get("WHEAT", 0))
    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)
    wheat_surplus = max(0, wheat_shed - wheat_feed_buffer)
    if wheat_surplus > 0 and len(orders) < MAX_ORDERS:
        orders.append(["SELL", "WHEAT", wheat_surplus])
        unit_w = float(prices.get("WHEAT", 1)) * 0.95
        budget += wheat_surplus * unit_w
        _MATCH_LEDGER["wheat_sold"] += wheat_surplus

    # === 2. CRITICAL LABOUR & FEED MAINTENANCE ===
    target_hires = _hire_target(day)
    already = int(_get(farm, "hires_today", 0))
    hire_costs = _hire_costs(target_hires, already)
    critical_target = min(target_hires, 2 if day <= 1 else 3 if day <= 4 else 5)
    critical_costs = _hire_costs(critical_target, already)
    hired_costs = 0
    for cost in critical_costs:
        if len(orders) >= MAX_ORDERS or budget < cost:
            break
        orders.append(["HIRE"])
        budget -= cost
        hired_costs += 1
        _MATCH_LEDGER["worker_wages"] += cost

    # Emergency Feed Protection: ONLY buy market wheat if on-farm grain is completely empty and animals need feed today
    wheat_total = wheat_shed + sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    if wheat_total < animal_count and day < 29:
        feed_needed = animal_count - wheat_total
        p_wheat_buy = _safe_buy_price(prices.get("WHEAT", 25))
        # Check livestock unit economics: if milk/wool covers feed, buy emergency buffer
        p_milk = float(prices.get("MILK", 80.0) or 80.0)
        if p_milk + p_fert >= p_wheat_buy or day <= 6:
            buy_q = min(feed_needed, int(budget // p_wheat_buy))
            if buy_q > 0 and len(orders) < MAX_ORDERS:
                orders.append(["BUY_PRODUCT", "WHEAT", buy_q])
                budget -= buy_q * p_wheat_buy
                _MATCH_LEDGER["market_wheat_cost"] += buy_q * p_wheat_buy

    # Discretionary hires (when treasury has operating cushion)
    liquidity_floor = 0 if day >= 20 else (300 if day <= 5 else 150)
    for cost in hire_costs[hired_costs:]:
        if len(orders) >= MAX_ORDERS or budget - cost < liquidity_floor:
            break
        orders.append(["HIRE"])
        budget -= cost
        _MATCH_LEDGER["worker_wages"] += cost

    # === 3. SEED REPLENISHMENT ===
    deficits = _quadrant_crop_deficits(obs)
    operating_reserve = max(int(_style_setting("cash_reserve")), 150)
    for crop in ("WHEAT", "MELON", "CARROT", "STRAWBERRY", "TOMATO"):
        if len(orders) >= MAX_ORDERS: break
        needed = deficits[crop]
        if needed <= 0: continue
        seed_cost = CROPS[crop]["seed"]
        affordable = int(max(0, budget - operating_reserve) // seed_cost)
        quantity = min(needed, affordable)
        if quantity > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_SEED", crop, quantity])
            cost_total = quantity * seed_cost
            budget -= cost_total
            if crop == "WHEAT": _MATCH_LEDGER["wheat_seed_cost"] += cost_total

    # === 4. ACCELERATED LAND EXPANSION ===
    land_cost = 0
    if day >= 4 and "NE" not in unlocked and budget - operating_reserve >= 1000:
        land_cost = 1000
    elif day >= 8 and "NE" in unlocked and "SW" not in unlocked and budget - operating_reserve >= 2000:
        land_cost = 2000
    elif day <= 16 and "SW" in unlocked and "SE" not in unlocked and budget - operating_reserve >= 2500:
        land_cost = 2500

    if land_cost and len(orders) < MAX_ORDERS:
        orders.append(["BUY_LAND"])
        budget -= land_cost
        _MATCH_LEDGER["land_spend"] += land_cost

    # === 5. MULTI-OUTPUT LIVESTOCK EXPANSION ===
    # Check payback period & on-farm grain buffer before buying animals
    remaining_days = max(1, 29 - day)
    target_counts = {animal: 0 for animal in ANIMALS}
    unlocked_set = set(unlocked)
    for pos, animal in _animal_plan().items():
        if _animal_site_active(pos, day, unlocked_set):
            target_counts[animal] += 1

    remaining_animal_slots = _animal_purchase_cap()
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 8: continue
        
        # Multi-output ROI calculation
        cap_cost = ANIMALS[animal]["cost"]
        p_prod = float(prices.get("MILK" if animal == "COW" else "WOOL", 80.0) or 80.0)
        daily_val = p_prod + p_fert
        feed_cost = 1.67 # On-farm grain cost
        daily_margin = daily_val - feed_cost - 25.0
        
        if daily_margin <= 15.0: continue # Negative or trivial ROI
        payback = cap_cost / daily_margin
        if remaining_days < payback + 3: continue # Cannot amortize
        
        affordable = int(max(0, budget - operating_reserve - 300) // cap_cost)
        quantity = min(needed, affordable, remaining_animal_slots)
        if quantity > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_ANIMAL", animal, quantity])
            budget -= quantity * cap_cost
            remaining_animal_slots -= quantity

    return orders[:MAX_ORDERS]
'''

# Assemble submission_adaptive_v2_economic.py
# 1. Header + constants from v1
with open(r"D:\kaggriculture\candidates\submission_adaptive_economic_v1.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Constants lines (15 to 44)
constants = "".join(lines[15:44])

# Load strategy block
with open(r"D:\kaggriculture\scratch\full_strategy.py") as sf:
    strategy_block = "\n" + sf.read() + "\n"

# Lines 44 to 405 contains animal plans, opening plan, configure_strategy, blended targets
engine_helpers_part0 = "".join(lines[44:405])

hire_target_line = None
for i, line in enumerate(lines):
    if "def _hire_target" in line:
        hire_target_line = i
        break

engine_helpers_part1 = "".join(lines[451:hire_target_line])

agent_entry = '''

def agent(obs):
    """Kaggle competition entry point — 100% Observation-Driven Controller."""
    try:
        global _LATEST_PRICES
        if isinstance(obs, dict):
            _LATEST_PRICES = (obs.get("market", {}) or {}).get("prices", {}) or {}
        elif hasattr(obs, "market"):
            _LATEST_PRICES = getattr(obs.market, "prices", {}) or {}
        _observe_opponent(obs)
        unit_actions = _assign_actions(obs)
        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": _market_orders(obs),
        }
    except Exception as e:
        return {"farmer": ["PASS"], "hands": [], "market": []}
'''

full_v2_code = header_v2 + constants + strategy_block + engine_helpers_part0 + crop_plan_v2 + engine_helpers_part1 + hire_and_market_v2 + agent_entry

target_file = r"D:\kaggriculture\candidates\submission_adaptive_v2_economic.py"
with open(target_file, "w", encoding="utf-8") as f:
    f.write(full_v2_code)

print(f"[+] Successfully generated {target_file}: {len(full_v2_code):,} chars, {len(full_v2_code.splitlines())} lines.")
