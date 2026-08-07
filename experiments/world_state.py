"""World-State Evaluator for Kaggle Agriculture.

Analyzes raw observation data to produce a structured, high-level evaluation
of the farm state every turn.

Metrics evaluated:
- Cash & Liquidity
- Land Occupancy & Unlocked Quadrants
- Animal Count & Feed Runway (Days of feed remaining)
- Active Crops & Yield Outlook
- Worker Count & Estimated Labor Load
- Emergency Flags (Feed shortage, Low liquidity, Labor saturation)
"""

import sys
import os

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 24, "val": 90},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False, "last_plant": 25, "val": 100},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True, "last_plant": 17, "val": 350},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True, "last_plant": 14, "val": 1000},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False, "last_plant": 16, "val": 1800},
}

ANIMALS = {
    "COW": {"cost": 400, "product": "MILK", "val": 270, "cadence": 1.5},
    "SHEEP": {"cost": 500, "product": "WOOL", "val": 170, "cadence": 3.1},
    "GOOSE": {"cost": 200, "product": "EGG", "val": 80, "cadence": 1.0},
}


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def evaluate_world_state(obs) -> dict:
    """Evaluates full world state from observation dictionary."""
    player = int(_get(obs, "player", 0))
    farms = _get(obs, "farms", [])
    farm = farms[player] if len(farms) > player else {}
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    inventories = _get(private, "inventories", []) or []
    market = _get(obs, "market", {}) or {}

    day = int(_get(obs, "day", 0))
    hour = int(_get(obs, "hour", 0))
    remaining_days = 29 - day

    money = float(_get(farm, "money", 0))
    unlocked = list(_get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    unlocked_set = set(unlocked)

    # 1. Land & Tile Occupancy
    tiles = _get(farm, "tiles", [])
    total_unlocked_tiles = len(unlocked) * 25 - 4  # 4 access/shed tiles
    occupied_tiles = 0
    empty_unlocked_tiles = 0
    crop_counts = {crop: 0 for crop in CROPS}
    animal_counts = {animal: 0 for animal in ANIMALS}
    ready_harvests = 0
    unfed_animals = 0
    consecutive_unfed_max = 0

    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict):
                continue
            # Check quadrant
            quad = "NW" if x < 5 and y < 5 else "NE" if y < 5 else "SW" if x < 5 else "SE"
            if quad not in unlocked_set:
                continue

            kind = tile.get("kind")
            if kind == "PLANT":
                occupied_tiles += 1
                crop = tile.get("crop")
                if crop in crop_counts:
                    crop_counts[crop] += 1
                if float(tile.get("yield_units", 0)) > 0:
                    ready_harvests += 1
            elif kind == "PASTURE":
                occupied_tiles += 1
                animal = tile.get("animal")
                if animal in animal_counts:
                    animal_counts[animal] += 1
                if animal and not tile.get("fed_today", False):
                    unfed_animals += 1
                    consecutive_unfed_max = max(consecutive_unfed_max, int(tile.get("consecutive_unfed", 0)))
                if float(tile.get("yield_units", 0)) > 0:
                    ready_harvests += 1
            elif kind is None or kind == "WEED":
                empty_unlocked_tiles += 1

    occupancy_ratio = occupied_tiles / max(1, total_unlocked_tiles)

    # 2. Feed Runway & Demand
    total_animals = sum(animal_counts.values())
    total_wheat = int(shed.get("WHEAT", 0)) + sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    daily_feed_demand = total_animals
    feed_runway_days = (total_wheat / max(1, daily_feed_demand)) if daily_feed_demand > 0 else 99.0

    # 3. Worker & Labor Capacity
    num_hands = len(_get(farm, "hands", []) or [])
    num_workers = 1 + num_hands

    # 4. Expected Daily Revenue
    daily_animal_rev = sum(animal_counts[a] * (ANIMALS[a]["val"] / ANIMALS[a]["cadence"]) for a in ANIMALS)
    daily_crop_rev = (crop_counts["STRAWBERRY"] * (1000 / 5.0)) + (crop_counts["TOMATO"] * (350 / 8.0))
    expected_daily_revenue = daily_animal_rev + daily_crop_rev

    # 5. Emergency Flags
    emergency_feed_shortage = (feed_runway_days < 1.5 and total_animals > 0 and day < 28) or consecutive_unfed_max >= 1
    low_liquidity_flag = money < 500 and day < 20
    labor_saturated_flag = (occupied_tiles / max(1, num_workers)) > 5.5
    under_occupied_flag = occupancy_ratio < 0.70 and len(unlocked) > 1

    return {
        "day": day,
        "hour": hour,
        "remaining_days": remaining_days,
        "money": money,
        "unlocked_quadrants": unlocked,
        "total_unlocked_tiles": total_unlocked_tiles,
        "occupied_tiles": occupied_tiles,
        "empty_unlocked_tiles": empty_unlocked_tiles,
        "occupancy_ratio": round(occupancy_ratio, 3),
        "crop_counts": crop_counts,
        "animal_counts": animal_counts,
        "total_animals": total_animals,
        "total_wheat": total_wheat,
        "daily_feed_demand": daily_feed_demand,
        "feed_runway_days": round(feed_runway_days, 1),
        "num_workers": num_workers,
        "ready_harvests": ready_harvests,
        "unfed_animals": unfed_animals,
        "expected_daily_revenue": round(expected_daily_revenue, 1),
        "flags": {
            "feed_emergency": emergency_feed_shortage,
            "low_liquidity": low_liquidity_flag,
            "labor_saturated": labor_saturated_flag,
            "under_occupied": under_occupied_flag,
        }
    }
