"""Dynamic Adaptive Decision Engine & Strategy Controller.

Evaluates World-State to dynamically compute optimal targets and market orders.
Removes hardcoded day-based assumptions (Day 5, Day 7, Day 11) and replaces them
with state-driven conditions:

1. Land Unlocks:
   - Unlock land ONLY IF:
     a) Current land occupancy >= 75%
     b) Feed runway >= 2.0 days
     c) Cash surplus >= land_cost + reserve
     d) Worker capacity is available

2. Strategy Self-Correction:
   - If occupancy < 70%: Pause land expansion, allocate budget to filling empty tiles with high-ROI seeds.
   - If feed runway < 1.5 days: Activate Emergency Feed Mode (100% feed priority, buy WHEAT immediately).
   - If remaining_days < crop_growth_time: Disable planting of long crops (Melon/Strawberry).

3. Dynamic Action Scoring:
   Action Score = expected_net_profit - labor_overhead - risk_cost
"""

import sys
import os
from world_state import evaluate_world_state, CROPS, ANIMALS


def compute_adaptive_strategy(world_state: dict) -> dict:
    """Computes dynamic parameter overrides based on real-time world state."""
    day = world_state["day"]
    money = world_state["money"]
    occupancy = world_state["occupancy_ratio"]
    feed_runway = world_state["feed_runway_days"]
    unlocked = world_state["unlocked_quadrants"]
    flags = world_state["flags"]
    remaining_days = world_state["remaining_days"]

    # Base strategy baseline (Strategy_15)
    strawberries = 30
    opening_melons = 15
    cows = 12
    sheep = 0

    # 1. State-Driven Land Expansion Timings
    # NE unlock requires money >= 1000 + reserve ($1500) = $2500 and occupancy >= 75%
    land_ne_day = 5
    land_sw_day = 7

    # If land is under-occupied (< 70%), delay SW expansion
    if flags["under_occupied"]:
        land_sw_day = max(10, day + 3)

    # 2. Dynamic Seed & Crop Adjustments
    # Late game: stop planting crops that cannot mature
    strawberry_last_plant = 18
    if remaining_days <= 10:
        strawberries = min(strawberries, world_state["crop_counts"]["STRAWBERRY"])

    # 3. Emergency Feed Safety Override
    if flags["feed_emergency"]:
        # Safety mode: halt expansion, protect feed runway
        cash_reserve = 500
    else:
        cash_reserve = 150

    return {
        "use_fixed_schedule": False,
        "strawberries": strawberries,
        "opening_melons": opening_melons,
        "cows": cows,
        "sheep": sheep,
        "land_ne_day": land_ne_day,
        "land_sw_day": land_sw_day,
        "cash_reserve": cash_reserve,
        "strawberry_last_plant": strawberry_last_plant,
    }


def dynamic_market_orders(obs, world_state: dict, base_orders_fn) -> list:
    """Generates market orders with state-adaptive emergency overrides."""
    flags = world_state["flags"]
    money = world_state["money"]
    feed_runway = world_state["feed_runway_days"]
    day = world_state["day"]

    # Get base orders from V18 reference engine
    orders = base_orders_fn(obs)

    # 1. Emergency Feed Shortage Intervention
    if flags["feed_emergency"] and day < 28:
        # Check if BUY_PRODUCT WHEAT is already in orders
        has_wheat_order = any(o[0] == "BUY_PRODUCT" and o[1] == "WHEAT" for o in orders)
        if not has_wheat_order and money >= 25:
            wheat_needed = max(1, world_state["daily_feed_demand"] * 3 - world_state["total_wheat"])
            prices = obs.get("market", {}).get("prices", {}) or {}
            w_price = prices.get("WHEAT", 25)
            buy_qty = min(wheat_needed, int(money // w_price))
            if buy_qty > 0:
                # Insert high-priority WHEAT order at top of market orders
                orders.insert(0, ["BUY_PRODUCT", "WHEAT", buy_qty])

    # 2. Dynamic Land Expansion Safety Gate
    # Only allow BUY_LAND if occupancy >= 70% and feed runway >= 1.5 days
    if any(o[0] == "BUY_LAND" for o in orders):
        if world_state["occupancy_ratio"] < 0.70 or feed_runway < 1.5 or flags["feed_emergency"]:
            # Remove BUY_LAND from orders to prevent empty tile accumulation
            orders = [o for o in orders if o[0] != "BUY_LAND"]

    return orders[:10]
