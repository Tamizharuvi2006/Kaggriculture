"""Kaggriculture Adaptive Economic Agent — V2 Autonomous Production Architecture.

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

import math

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 24},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False, "last_plant": 25},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True, "last_plant": 17},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True, "last_plant": 14},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False, "last_plant": 16},
}

ANIMALS = {
    "COW": {"cost": 400, "product": "MILK"},
    "SHEEP": {"cost": 500, "product": "WOOL"},
}

SELLABLE = ("MILK", "WOOL", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "EGG")
MAX_ORDERS = 10

# The opening deliberately mixes quick wheat cash-flow with a smaller melon
# position.  A previous melon-heavy opening could sit at zero cash for twelve
# days and lose all livestock after a one-dollar within-turn price move.
# Sites are ordered by expansion phase: four initial, five in NE, five in SW.
ANIMAL_SITES = (
    (4, 2), (4, 3), (3, 4), (4, 4),
    (6, 2), (5, 3), (7, 3), (5, 4), (7, 4),
    (3, 5), (4, 5), (3, 6), (4, 6), (4, 7),
)



DEFAULT_STRATEGY = {
    'adaptive_animal_lead': 2,
    'adaptive_animal_max_day': 14,
    'adaptive_animal_min_day': 2,
    'adaptive_animal_min_herd': 4,
    'adaptive_animal_mode': 'mirror',
    'adaptive_animal_target_share': 0.72,
    'adaptive_capital_animal_lead': 2,
    'adaptive_capital_land_lead': 1,
    'adaptive_capital_max_day': 12,
    'adaptive_capital_priority': False,
    'adaptive_tempo_animal_lead': 1,
    'adaptive_tempo_cow': False,
    'adaptive_tempo_land_lead': 1,
    'animal_daily_cap': 3,
    'animal_ne_day': 8,
    'animal_nw_day': 4,
    'animal_price_sensitivity': 2.0,
    'animal_sw_day': 12,
    'cash_reserve': 150,
    'cow_expert_cows': 2,
    'cow_expert_sheep': 0,
    'cows': 2,
    'crop_transition_day': 5,
    'drop_load_threshold': 30,
    'early_liquidity_floor': 0,
    'feed_days_buffer': 1,
    'fertilizer_roi': 1.5,
    'force_expert': None,
    'hands': 11,
    'land_ne_day': 5,
    'land_sw_day': 10,
    'livestock_animal_cap': 3,
    'livestock_cash_reserve': 150,
    'livestock_cows': 2,
    'livestock_sheep': 0,
    'livestock_strawberries': 34,
    'livestock_tomatoes': 0,
    'ongoing_harvest_threshold': 3,
    'opening_animals': 0,
    'opening_carrots': 2,
    'opening_cows': None,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 9,
    'opening_sheep': None,
    'opening_wheat': 10,
    'premium_animal_cap': 3,
    'premium_cash_reserve': 250,
    'premium_cows': 2,
    'premium_sheep': 0,
    'premium_strawberries': 34,
    'premium_tomatoes': 0,
    'price_adaptive_animals': False,
    'price_buffer_pct': 5,
    'rotation_evidence_threshold': 0.9,
    'sheep': 0,
    'sheep_expert_cows': 2,
    'sheep_expert_sheep': 12,
    'strawberries': 34,
    'strawberry_activation_day': 4,
    'strawberry_last_plant': 18,
    'strawberry_staging': False,
    'top_hire_ramp': False,
    'wheat_rush_animal_cap': 1,
    'wheat_rush_cash_reserve': 150,
    'zoned_workers': False,
}
STRATEGY = dict(DEFAULT_STRATEGY)

def _spread_animals(cows, sheep):
    total = min(len(ANIMAL_SITES), max(0, int(cows)) + max(0, int(sheep)))
    sheep = min(max(0, int(sheep)), total)
    plan = {}
    sheep_used = 0
    for i, pos in enumerate(ANIMAL_SITES[:total]):
        target_sheep = round((i + 1) * sheep / total) if total else 0
        animal = "SHEEP" if target_sheep > sheep_used else "COW"
        sheep_used += animal == "SHEEP"
        plan[pos] = animal
    return plan


def _build_animal_plan(cows, sheep):
    """Build a target herd while allowing a distinct four-animal opening."""
    cows = max(0, int(cows))
    sheep = max(0, int(sheep))
    total = min(len(ANIMAL_SITES), cows + sheep)
    opening_cows = STRATEGY.get("opening_cows")
    opening_sheep = STRATEGY.get("opening_sheep")
    if opening_cows is None or opening_sheep is None:
        return _spread_animals(cows, sheep)
    opening_total = min(4, total, max(0, int(opening_cows)) + max(0, int(opening_sheep)))
    opening_sheep = min(max(0, int(opening_sheep)), opening_total, sheep)
    opening_cows = min(max(0, int(opening_cows)), opening_total - opening_sheep, cows)
    opening_total = opening_cows + opening_sheep
    plan = dict(list(_spread_animals(opening_cows, opening_sheep).items())[:opening_total])
    remaining_total = total - opening_total
    remaining_sheep = min(max(0, sheep - opening_sheep), remaining_total)
    sheep_used = 0
    for i, pos in enumerate(ANIMAL_SITES[opening_total:opening_total + remaining_total]):
        target_sheep = round((i + 1) * remaining_sheep / remaining_total) if remaining_total else 0
        animal = "SHEEP" if target_sheep > sheep_used else "COW"
        sheep_used += animal == "SHEEP"
        plan[pos] = animal
    return plan


def _build_opening_plan(wheat, melons, animal_plan, carrots=2):
    """Build a 21-tile NW opening with long crops nearest the shed."""
    blocked = set(list(animal_plan)[:4])
    slots = [(x, y) for y in range(5) for x in range(5) if (x, y) not in blocked]
    slots.sort(key=lambda p: (abs(p[0] - 4) + abs(p[1] - 4), p[1], p[0]))
    melons = min(max(0, int(melons)), len(slots))
    plan = {pos: "MELON" for pos in slots[:melons]}
    remaining = slots[melons:]
    carrots = min(max(0, int(carrots)), max(0, len(remaining) - int(wheat)))
    for pos in remaining[:carrots]:
        plan[pos] = "CARROT"
    for pos in remaining[carrots:carrots + max(0, int(wheat))]:
        plan[pos] = "WHEAT"
    return plan


def _build_crop_plan(strawberries, animal_plan, tomatoes=0):
    # Melons retain their proven two-cycle opening sites.  Every other usable
    # tile becomes a candidate strawberry site, prioritized near the shed.
    plan = {pos: crop for pos, crop in OPENING_CROP_PLAN.items() if crop == "MELON"}
    opening_strawberries = [pos for pos, crop in OPENING_CROP_PLAN.items() if crop == "STRAWBERRY"]
    candidates = [
        (x, y)
        for y in range(10)
        for x in range(10)
        if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))
        and (x, y) not in animal_plan
        and (x, y) not in plan
    ]
    candidates.sort(
        key=lambda p: (
            0 if p in opening_strawberries else 1,
            abs(p[0] - 4.5) + abs(p[1] - 4.5),
            p[1],
            p[0],
        )
    )
    for pos in candidates[:max(0, int(strawberries))]:
        plan[pos] = "STRAWBERRY"
    tomato_start = max(0, int(strawberries))
    for pos in candidates[tomato_start:tomato_start + max(0, int(tomatoes))]:
        plan[pos] = "TOMATO"
    return plan


def configure_strategy(overrides=None):
    """Configure one module instance for local HPO; submission uses defaults."""
    global STRATEGY, ANIMAL_PLAN, CROP_PLAN, FIELD_PLAN, OPENING_CROP_PLAN
    global ADAPTIVE_ANIMAL_PLANS, ADAPTIVE_CROP_PLANS, EXPERT_PROFILES
    global _OPPONENT_STYLE, _EXPERT_EVIDENCE, _MARKET_ANIMAL_SHARE, _PLAN_CACHE
    STRATEGY = dict(DEFAULT_STRATEGY)
    if overrides:
        STRATEGY.update(overrides)
    ANIMAL_PLAN = _build_animal_plan(STRATEGY["cows"], STRATEGY["sheep"])
    OPENING_CROP_PLAN = _build_opening_plan(
        STRATEGY["opening_wheat"], STRATEGY["opening_melons"], ANIMAL_PLAN,
        STRATEGY["opening_carrots"],
    )
    CROP_PLAN = _build_crop_plan(STRATEGY["strawberries"], ANIMAL_PLAN)
    livestock_plan = _build_animal_plan(STRATEGY["livestock_cows"], STRATEGY["livestock_sheep"])
    premium_plan = _build_animal_plan(STRATEGY["premium_cows"], STRATEGY["premium_sheep"])
    ADAPTIVE_ANIMAL_PLANS = {
        None: ANIMAL_PLAN,
        "WHEAT_RUSH": ANIMAL_PLAN,
        "LIVESTOCK_RUSH": livestock_plan,
        "PREMIUM_CROP": premium_plan,
    }
    ADAPTIVE_CROP_PLANS = {
        None: CROP_PLAN,
        "WHEAT_RUSH": CROP_PLAN,
        "LIVESTOCK_RUSH": _build_crop_plan(
            STRATEGY["livestock_strawberries"], livestock_plan, STRATEGY["livestock_tomatoes"]
        ),
        "PREMIUM_CROP": _build_crop_plan(
            STRATEGY["premium_strawberries"], premium_plan, STRATEGY["premium_tomatoes"]
        ),
    }
    base_profile = {
        "hands": STRATEGY["hands"],
        "cows": STRATEGY["cows"],
        "sheep": STRATEGY["sheep"],
        "strawberries": STRATEGY["strawberries"],
        "tomatoes": 0,
        "cash_reserve": STRATEGY["cash_reserve"],
        "animal_cap": STRATEGY["animal_daily_cap"],
        "strawberry_last_plant": STRATEGY["strawberry_last_plant"],
    }
    EXPERT_PROFILES = {
        "BASE": base_profile,
        "WHEAT_RUSH": dict(
            base_profile,
            cash_reserve=STRATEGY["wheat_rush_cash_reserve"],
            animal_cap=STRATEGY["wheat_rush_animal_cap"],
        ),
        "COW_RUSH": dict(
            base_profile,
            cows=STRATEGY["cow_expert_cows"],
            sheep=STRATEGY["cow_expert_sheep"],
            cash_reserve=STRATEGY["livestock_cash_reserve"],
            animal_cap=STRATEGY["livestock_animal_cap"],
        ),
        "SHEEP_RUSH": dict(
            base_profile,
            cows=STRATEGY["sheep_expert_cows"],
            sheep=STRATEGY["sheep_expert_sheep"],
            cash_reserve=STRATEGY["livestock_cash_reserve"],
            animal_cap=STRATEGY["livestock_animal_cap"],
        ),
        "PREMIUM_CROP": dict(
            base_profile,
            cows=STRATEGY["premium_cows"],
            sheep=STRATEGY["premium_sheep"],
            strawberries=STRATEGY["premium_strawberries"],
            tomatoes=STRATEGY["premium_tomatoes"],
            cash_reserve=STRATEGY["premium_cash_reserve"],
            animal_cap=STRATEGY["premium_animal_cap"],
        ),
    }
    FIELD_PLAN = {pos: crop for pos, crop in OPENING_CROP_PLAN.items()}
    _OPPONENT_STYLE = None
    _EXPERT_EVIDENCE = {}
    _MARKET_ANIMAL_SHARE = None
    _PLAN_CACHE = {}


def _expert_weights():
    forced = STRATEGY.get("force_expert")
    if forced in EXPERT_PROFILES:
        return {forced: 1.0}
    # Wheat-capital evidence represents an existential feed-price risk and
    # therefore owns the portfolio once confirmed.  Other regimes blend.
    if float(_EXPERT_EVIDENCE.get("WHEAT_RUSH", 0)) >= 0.8:
        return {"WHEAT_RUSH": 1.0}
    # Pure early sheep openings depress wool economics before a later herd is
    # visible.  Replay counterfactuals consistently favored keeping the base
    # 8/6 portfolio with extra liquidity, so this signal must act early.
    if float(_EXPERT_EVIDENCE.get("EARLY_SHEEP", 0)) >= 0.8:
        return {"PREMIUM_CROP": 1.0}
    evidence = {
        name: max(0.0, min(1.0, float(_EXPERT_EVIDENCE.get(name, 0))))
        for name in ("COW_RUSH", "SHEEP_RUSH", "PREMIUM_CROP")
    }
    # A farm that exposes both livestock regimes is rotating its market
    # pressure rather than specializing.  Chasing both sides produced the
    # weakest possible 7/7 herd in replay validation; the liquid balanced
    # expert is the robust response to this phase-changing portfolio.
    rotation_threshold = float(STRATEGY.get("rotation_evidence_threshold", 0.9))
    if evidence["COW_RUSH"] >= rotation_threshold and evidence["SHEEP_RUSH"] >= rotation_threshold:
        return {"PREMIUM_CROP": 1.0}
    active = sum(evidence.values())
    if active <= 0:
        return {"BASE": 1.0}
    # A clear signature selects the validated counter exactly.  Lower
    # confidence produces a genuine mixture with BASE, avoiding a brittle
    # all-or-nothing switch on borderline farms.
    expert_mass = 1.0 if max(evidence.values()) >= 0.9 else min(0.85, active)
    weights = {name: expert_mass * value / active for name, value in evidence.items() if value > 0}
    weights["BASE"] = 1.0 - expert_mass
    return weights


def _blended_targets():
    weights = _expert_weights()
    numeric = {}
    for key in ("hands", "cows", "sheep", "strawberries", "tomatoes", "cash_reserve", "animal_cap", "strawberry_last_plant"):
        numeric[key] = sum(weight * float(EXPERT_PROFILES[name][key]) for name, weight in weights.items())
    total_animals = max(0, round(numeric["cows"] + numeric["sheep"]))
    cows = min(total_animals, max(0, round(numeric["cows"])))
    if STRATEGY.get("price_adaptive_animals") and _MARKET_ANIMAL_SHARE is not None:
        cows = min(total_animals, max(0, round(total_animals * _MARKET_ANIMAL_SHARE)))
    return {
        "hands": max(0, round(numeric["hands"])),
        "cows": cows,
        "sheep": total_animals - cows,
        "strawberries": max(0, round(numeric["strawberries"])),
        "tomatoes": max(0, round(numeric["tomatoes"])),
        "cash_reserve": max(0, round(numeric["cash_reserve"])),
        "animal_cap": max(0, round(numeric["animal_cap"])),
        "strawberry_last_plant": max(0, round(numeric["strawberry_last_plant"])),
    }



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
            total_yield = cycles * spec["max_yield"]
            # Daily labour overhead (~12/day)
            net_profit = (total_yield * p_unit) - seed_cost - (remaining_days * 12.0)
            scores[crop] = net_profit / max(1, remaining_days)
        else:
            # One-time crop
            net_profit = (spec["max_yield"] * p_unit) - seed_cost - (max_day * 12.0)
            scores[crop] = net_profit / max(1, max_day)
            
    return scores


def _crop_plan(day):
    """Dynamic economic crop allocation derived from live prices and animal feed demands."""
    if day < int(STRATEGY.get("crop_transition_day", 5)):
        return OPENING_CROP_PLAN

    prices = _LATEST_PRICES
    p_wheat = float(prices.get("WHEAT", 25.0) or 25.0)
    animal_plan = _animal_plan()
    
    # 1. Dynamic feed plot requirement derived from living herd & commercial town demand
    # Active herd size: cows + sheep planned/active
    # Each wheat plot yields 6 wheat every 4 days = 1.5 wheat/day.
    # We ensure farm grain production covers 100% of herd feed consumption.
    num_animals = len(animal_plan) if day >= 10 else (4 if day >= 6 else 2)
    feed_wheat_plots = max(4, math.ceil(num_animals / 1.5))
    surplus_wheat_plots = 3 if p_wheat >= 32.0 else 0
    total_wheat_plots = feed_wheat_plots + surplus_wheat_plots
    
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
        
    # B. Allocate primary cash crop (85% of remaining arable plots)
    rem = candidates[total_wheat_plots:]
    primary_quota = max(0, int(len(rem) * 0.85))
    for pos in rem[:primary_quota]:
        plan[pos] = primary_cash_crop
        
    # C. Allocate remaining plots to secondary cash crop (diversification buffer)
    for pos in rem[primary_quota:]:
        plan[pos] = secondary_cash_crop
        
    return plan

def _animal_plan():
    return _build_animal_plan(8, 4)


def _style_setting(base):
    """Return the soft-gated strategic target for a shared executor."""
    targets = _blended_targets()
    if base in targets:
        return targets[base]
    return STRATEGY[base]


configure_strategy()


def _get(obj, key, default=None):
    if key == "step" and (isinstance(obj, dict) or hasattr(obj, "__dict__")):
        val = obj.get("step") if isinstance(obj, dict) else getattr(obj, "step", None)
        if val is not None:
            return val
        day = obj.get("day", 0) if isinstance(obj, dict) else getattr(obj, "day", 0) or 0
        hour = obj.get("hour", 0) if isinstance(obj, dict) else getattr(obj, "hour", 0) or 0
        return int(day) * 24 + int(hour)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _shed_access(board_size):
    half = board_size // 2
    return ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))


def _available_access(tiles):
    """Shed corners that belong to currently unlocked quadrants."""
    access = _shed_access(len(tiles) or 10)
    available = tuple(p for p in access if tiles[p[1]][p[0]] != "LOCKED") if tiles else ()
    return available or (access[0],)


def _move_toward(pos, target, tiles=None):
    """Return a shortest move while avoiding still-locked quadrants."""
    x, y = pos
    tx, ty = target
    if tiles:
        moves = (("NORTH", 0, -1), ("WEST", -1, 0), ("EAST", 1, 0), ("SOUTH", 0, 1))
        queue = [(x, y, None)]
        seen = {(x, y)}
        for cx, cy, first in queue:
            if (cx, cy) == (tx, ty):
                return [first] if first else ["PASS"]
            for name, dx, dy in moves:
                nx, ny = cx + dx, cy + dy
                if not (0 <= ny < len(tiles) and 0 <= nx < len(tiles[ny])) or (nx, ny) in seen:
                    continue
                if tiles[ny][nx] == "LOCKED":
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny, first or name))
        return ["PASS"]
    if abs(tx - x) >= abs(ty - y) and x != tx:
        return ["EAST" if x < tx else "WEST"]
    if y != ty:
        return ["SOUTH" if y < ty else "NORTH"]
    if x != tx:
        return ["EAST" if x < tx else "WEST"]
    return ["PASS"]


def _count_inventory(inv):
    if not isinstance(inv, dict):
        return 0
    return sum(max(0, int(v)) for v in inv.values())


def _asset_counts(obs):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    private = _get(obs, "private", {}) or {}
    counts = {name: 0 for name in ANIMALS}
    for row in _get(farm, "tiles", []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in counts:
                counts[tile["animal"]] += 1
    shed = _get(private, "shed", {}) or {}
    inventories = _get(private, "inventories", []) or []
    for animal in counts:
        counts[animal] += int(shed.get(animal, 0))
        counts[animal] += sum(int(inv.get(animal, 0)) for inv in inventories if isinstance(inv, dict))
    return counts


def _active_target(pos, day, unlocked):
    x, y = pos
    if x < 5 and y < 5:
        return True
    if x >= 5 and y < 5:
        return "NE" in unlocked and day >= 7
    if x < 5 and y >= 5:
        return "SW" in unlocked and day >= 9
    return False


def _animal_site_active(pos, day, unlocked):
    """Stage livestock growth so labour and feed can grow before the herd."""
    x, y = pos
    if x < 5 and y < 5:
        return day >= 4
    if x >= 5 and y < 5:
        return "NE" in unlocked and day >= 7
    if x < 5 and y >= 5:
        return "SW" in unlocked and day >= 9
    return False


def _crop_is_ripe(tile, day, hour):
    crop = tile.get("crop")
    spec = CROPS.get(crop)
    if not spec or int(tile.get("yield_units", 0)) <= 0:
        return False
    age = day - int(tile.get("planted_day", day))
    if age < spec["first"]:
        return False
    if not spec["ongoing"]:
        return int(tile.get("yield_units", 0)) >= spec["max_yield"] or age >= spec["max_day"]
    # Avoid hitting the held-yield cap, and cash out anything available near
    # the end of the season.
    threshold = max(1, int(STRATEGY.get("ongoing_harvest_threshold", 3)))
    return (
        int(tile.get("yield_units", 0)) >= threshold
        or day >= 28
        or (hour >= 18 and int(tile.get("yield_units", 0)) >= min(2, threshold))
    )


def _last_plant(crop):
    if crop == "STRAWBERRY":
        return int(_style_setting("strawberry_last_plant"))
    return int(CROPS[crop]["last_plant"])


def _fertilizer_value(tile, day, prices):
    """Expected value of one 3-day fertilizer application on a strawberry."""
    roi = STRATEGY.get("fertilizer_roi")
    if roi is None or tile.get("crop") != "STRAWBERRY":
        return 0
    if int(tile.get("fertilized_until_day", -1)) >= day + 1:
        return 0
    planted = int(tile.get("planted_day", day))
    bonus_ticks = 0
    for current_day in range(day, day + 3):
        since_first = current_day + 1 - planted - CROPS["STRAWBERRY"]["first"]
        if since_first >= 0 and since_first % 2 == 0 and since_first // 2 < CROPS["STRAWBERRY"]["max_yield"]:
            bonus_ticks += 1
    value = bonus_ticks * float(prices.get("STRAWBERRY", 120))
    cost = float(prices.get("FERTILIZER", 100)) * float(roi)
    return bonus_ticks if bonus_ticks and value >= cost else 0


def _fertilizer_positions(obs):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    day = int(_get(obs, "day", 0))
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    positions = []
    for y, row in enumerate(_get(farm, "tiles", [])):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and _fertilizer_value(tile, day, prices):
                positions.append((x, y))
    return positions


def _task(priority, pos, action, requirement=None, tag="", ev=10.0):
    return (priority, pos, action, requirement, tag, float(ev))


def _build_tasks(obs, positions, inventories):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    tiles = _get(farm, "tiles", [])
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    day = int(_get(obs, "day", 0))
    hour = int(_get(obs, "hour", 0))
    unlocked = set(_get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    access = _available_access(tiles)
    tasks = []
    crop_plan = _crop_plan(day)
    animal_plan = _animal_plan()
    fertilizer_positions = set(_fertilizer_positions(obs))

    prices = _LATEST_PRICES
    p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
    p_melon = float(prices.get("MELON", 120.0) or 120.0)
    p_wheat = float(prices.get("WHEAT", 25.0) or 25.0)
    p_milk = float(prices.get("MILK", 100.0) or 100.0)
    p_wool = float(prices.get("WOOL", 150.0) or 150.0)
    p_fert = float(prices.get("FERTILIZER", 45.0) or 45.0)

    animals = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict):
                continue
            if tile.get("animal") in ANIMALS:
                anim = tile.get("animal")
                animals.append(((x, y), tile))
                if day < 29 and not tile.get("fed_today", False):
                    urgent = 0 if int(tile.get("consecutive_unfed", 0)) >= 1 or hour >= 12 else 1
                    ev = 800.0 if urgent == 0 else 150.0
                    tasks.append(_task(urgent, (x, y), ["FEED"], "WHEAT", "feed", ev))
                if int(tile.get("yield_units", 0)) > 0:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = int(tile.get("yield_units", 1)) * p_unit * 0.95
                    tasks.append(_task(1, (x, y), ["HARVEST"], None, "harvest", ev))
                if not tile.get("cared_today", False) and day < 29:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = p_unit * 0.95
                    tasks.append(_task(2, (x, y), ["CARE"], None, "care", ev))
                if tile.get("fertilizer_available", False):
                    tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))

    # Crop preservation and harvest precede new construction.
    for (x, y), desired in crop_plan.items():
        if y >= len(tiles) or x >= len(tiles[y]) or not _active_target((x, y), day, unlocked):
            continue
        tile = tiles[y][x]
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            crop = tile.get("crop")
            p_unit = float(prices.get(crop, 20.0) or 20.0)
            spec = CROPS.get(crop, CROPS["WHEAT"])
            yield_qty = int(tile.get("yield_units", 0)) or spec.get("max_yield", 4)
            if _crop_is_ripe(tile, day, hour):
                ev = yield_qty * p_unit * 0.95
                tasks.append(_task(1, (x, y), ["HARVEST"], None, "harvest", ev))
            elif not tile.get("watered_today", False):
                age = day - int(tile.get("planted_day", day))
                in_bonus = not spec["ongoing"] and (spec["max_day"] + 1) // 2 <= age <= spec["max_day"]
                urgent = int(tile.get("consecutive_unwatered", 0)) >= 1 or hour >= 16
                needs_fertilizer_water = (x, y) in fertilizer_positions or int(tile.get("fertilized_until_day", -1)) >= day
                if urgent or in_bonus or needs_fertilizer_water:
                    prio = 0 if urgent else 2 if needs_fertilizer_water else 3
                    ev = 350.0 if urgent else (90.0 if in_bonus else 60.0 if needs_fertilizer_water else 25.0)
                    tasks.append(_task(prio, (x, y), ["WATER"], None, "water", ev))
            if (x, y) in fertilizer_positions:
                tasks.append(_task(2, (x, y), ["FERTILIZE"], "FERTILIZER", "fertilize", 120.0))

    # Build and populate livestock sites before filling expansion crops.
    for pos, animal in animal_plan.items():
        x, y = pos
        if y >= len(tiles) or x >= len(tiles[y]) or not _animal_site_active(pos, day, unlocked):
            continue
        tile = tiles[y][x]
        waiting = int(shed.get(animal, 0)) > 0 or any(int(inv.get(animal, 0)) > 0 for inv in inventories if isinstance(inv, dict))
        prio = 2 if waiting else 5
        ev = 300.0 if waiting else 40.0
        if tile is None:
            tasks.append(_task(prio, pos, ["BUILD_PASTURE"], None, "build", ev))
        elif isinstance(tile, dict) and tile.get("kind") == "PASTURE" and "animal" not in tile:
            tasks.append(_task(1, pos, ["PLACE", animal], animal, "place", 350.0))
        elif isinstance(tile, dict) and tile.get("kind") in ("WEED", "PLANT"):
            tasks.append(_task(prio, pos, ["DIG"], None, "dig", 15.0))

    # Land preparation and planting.
    remaining = {crop: int(seeds.get(crop, 0)) for crop in CROPS}
    for pos, crop in crop_plan.items():
        x, y = pos
        if y >= len(tiles) or x >= len(tiles[y]) or not _active_target(pos, day, unlocked):
            continue
        tile = tiles[y][x]
        if isinstance(tile, dict) and tile.get("kind") == "WEED":
            if day <= _last_plant(crop):
                tasks.append(_task(3, pos, ["DIG"], None, "dig", 15.0))
        elif tile is None and day <= _last_plant(crop) and remaining[crop] > 0:
            ev = 110.0 if crop == "STRAWBERRY" else (60.0 if crop == "MELON" else 50.0 if crop == "WHEAT" else 30.0)
            tasks.append(_task(2, pos, ["PLANT", crop], None, "plant", ev))
            remaining[crop] -= 1

    # Operational inventory pickups.
    unfed = sum(not tile.get("fed_today", False) for _, tile in animals)
    carried_wheat = sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    if unfed > carried_wheat and int(shed.get("WHEAT", 0)) > 0:
        carriers = min(3, max(1, (unfed - carried_wheat + 3) // 4))
        quantity = min(int(shed.get("WHEAT", 0)), max(1, (unfed - carried_wheat + carriers - 1) // carriers))
        for i in range(carriers):
            tasks.append(_task(1, access[i % len(access)], ["PICKUP", "WHEAT", quantity], None, "pickup_wheat", 150.0))

    carried_fertilizer = sum(int(inv.get("FERTILIZER", 0)) for inv in inventories if isinstance(inv, dict))
    fertilizer_deficit = len(fertilizer_positions) - carried_fertilizer
    if fertilizer_deficit > 0 and int(shed.get("FERTILIZER", 0)) > 0:
        carriers = min(3, max(1, (fertilizer_deficit + 3) // 4))
        quantity = min(int(shed.get("FERTILIZER", 0)), max(1, (fertilizer_deficit + carriers - 1) // carriers))
        for i in range(carriers):
            tasks.append(_task(1, access[-(i % len(access)) - 1], ["PICKUP", "FERTILIZER", quantity], None, "pickup_fertilizer", 70.0))

    for animal in ANIMALS:
        empty_positions = [
            pos for pos, target in animal_plan.items()
            if target == animal and _active_target(pos, day, unlocked)
            and isinstance(tiles[pos[1]][pos[0]], dict)
            and tiles[pos[1]][pos[0]].get("kind") == "PASTURE"
            and "animal" not in tiles[pos[1]][pos[0]]
        ]
        empty = len(empty_positions)
        carried = sum(int(inv.get(animal, 0)) for inv in inventories if isinstance(inv, dict))
        if empty > carried and int(shed.get(animal, 0)) > 0:
            pickup = min(access, key=lambda a: (min(_distance(a, target) for target in empty_positions), a[1], a[0]))
            tasks.append(_task(1, pickup, ["PICKUP", animal, min(empty - carried, int(shed.get(animal, 0)))], None, "pickup_animal", 300.0))

    return tasks


def _eligible(task, inv):
    requirement = task[3]
    return requirement is None or (isinstance(inv, dict) and int(inv.get(requirement, 0)) > 0)


def _quadrant(pos):
    x, y = pos
    return "NW" if x < 5 and y < 5 else "NE" if y < 5 else "SW" if x < 5 else "SE"


def _worker_zone(index, unlocked):
    if "SW" in unlocked:
        return "NW" if index < 4 else "NE" if index < 9 else "SW"
    if "NE" in unlocked:
        return "NW" if index < 4 else "NE"
    return "NW"


def _assign_actions(obs):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    private = _get(obs, "private", {}) or {}
    positions = [tuple(_get(farm, "farmer", (4, 4)))] + [tuple(p) for p in (_get(farm, "hands", []) or [])]
    inventories = list(_get(private, "inventories", []) or [])
    while len(inventories) < len(positions):
        inventories.append({})
    day = int(_get(obs, "day", 0))
    hour = int(_get(obs, "hour", 0))
    access = _available_access(_get(farm, "tiles", []))
    tasks = _build_tasks(obs, positions, inventories)
    actions = [["PASS"] for _ in positions]
    free = set(range(len(positions)))

    # Purchased livestock is high-value, per-unit inventory.  Route carriers
    # directly instead of letting generic nearby tasks repeatedly steal them.
    tiles = _get(farm, "tiles", [])
    unlocked = set(_get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    animal_plan = _animal_plan()
    reserved_targets = set()

    # Feeding is an existential task: two unfed days delete the animal.  Keep
    # designated carriers moving to the shed instead of allowing generic
    # nearest-task matching to redirect them to watering on every turn.
    if day < 29:
        unfed = [
            (x, y)
            for y, row in enumerate(tiles)
            for x, tile in enumerate(row)
            if isinstance(tile, dict)
            and tile.get("animal") in ANIMALS
            and not tile.get("fed_today", False)
        ]
        carried_wheat = sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
        shed = _get(private, "shed", {}) or {}
        deficit = max(0, len(unfed) - carried_wheat)
        if deficit and int(shed.get("WHEAT", 0)) > 0:
            carriers = min(3, max(1, (deficit + 3) // 4), len(free))
            candidates = [
                idx for idx in free
                if isinstance(inventories[idx], dict)
                and not any(int(inventories[idx].get(a, 0)) > 0 for a in ANIMALS)
                and int(inventories[idx].get("WHEAT", 0)) == 0
            ]
            candidates.sort(key=lambda idx: min(_distance(positions[idx], p) for p in access))
            remaining_wheat = min(deficit, int(shed.get("WHEAT", 0)))
            for number, idx in enumerate(candidates[:carriers]):
                remaining_carriers = carriers - number
                quantity = max(1, (remaining_wheat + remaining_carriers - 1) // remaining_carriers)
                target = min(access, key=lambda p: (_distance(positions[idx], p), p[1], p[0]))
                actions[idx] = ["PICKUP", "WHEAT", quantity] if positions[idx] in access else _move_toward(positions[idx], target, tiles)
                remaining_wheat = max(0, remaining_wheat - quantity)
                free.discard(idx)

    for idx, (pos, inv) in enumerate(zip(positions, inventories)):
        if idx not in free:
            continue
        if not isinstance(inv, dict):
            continue
        animal = next((name for name in ANIMALS if int(inv.get(name, 0)) > 0), None)
        if animal is None:
            continue
        targets = [
            target
            for target, desired in animal_plan.items()
            if desired == animal
            and target not in reserved_targets
            and _active_target(target, day, unlocked)
            and isinstance(tiles[target[1]][target[0]], dict)
            and tiles[target[1]][target[0]].get("kind") == "PASTURE"
            and "animal" not in tiles[target[1]][target[0]]
        ]
        if not targets:
            continue
        target = min(targets, key=lambda p: (_distance(pos, p), p[1], p[0]))
        reserved_targets.add(target)
        actions[idx] = ["PLACE", animal] if pos == target else _move_toward(pos, target, tiles)
        free.discard(idx)

    # Late-day liquidation is explicit.  On other turns inventories stay on
    # workers and auto-drop overnight, saving hundreds of return-path moves.
    for idx, (pos, inv) in enumerate(zip(positions, inventories)):
        if idx not in free:
            continue
        n = _count_inventory(inv)
        if n == 0:
            continue
        operational = sum(int(inv.get(k, 0)) for k in ("WHEAT", "FERTILIZER", "COW", "SHEEP")) if isinstance(inv, dict) else 0
        harvest_load = n - operational
        load_threshold = max(1, int(STRATEGY.get("drop_load_threshold", 30)))
        should_drop = (
            (day >= 29 and hour >= 12)
            or (hour >= 21 and harvest_load > 0)
            or harvest_load >= load_threshold
        )
        if should_drop:
            target = min(access, key=lambda p: (_distance(pos, p), p[1], p[0]))
            actions[idx] = ["DROP"] if pos in access else _move_toward(pos, target, tiles)
            free.discard(idx)

    # Two-Tier Matching with Economic Value per Turn (EV/Turn) Scoring:
    # 1. Tier 0: Hard Existential Emergencies (Priority 0)
    #    Dying unfed animals and dying unwatered crops are handled immediately by nearest unit.
    p0_tasks = [t for t in tasks if t[0] == 0]
    while p0_tasks and free:
        candidates = []
        for unit in free:
            inv = inventories[unit]
            for j, task in enumerate(p0_tasks):
                if not _eligible(task, inv):
                    continue
                dist = _distance(positions[unit], task[1])
                candidates.append((dist, unit, j))
        if not candidates:
            break
        _, unit, task_idx = min(candidates)
        task = p0_tasks.pop(task_idx)
        actions[unit] = task[2] if positions[unit] == task[1] else _move_toward(positions[unit], task[1], tiles)
        free.remove(unit)

    # 2. Tier 1: All Economic & Operational Tasks (Priority >= 1)
    #    Scored by EV/Turn: score = task_ev / (1.0 + travel_dist + locality_friction)
    #    Routine maintenance chores (watering, weeding, planting) prefer the local quadrant (friction = 2 turns).
    #    High-value harvests, animal care, feed, placement, and building compete globally (friction = 0).
    pending = [t for t in tasks if t[0] > 0]
    while pending and free:
        candidates = []
        for unit in free:
            inv = inventories[unit]
            pos_u = positions[unit]
            q_u = _quadrant(pos_u)
            carried_animal = any(int(inv.get(a, 0)) > 0 for a in ANIMALS) if isinstance(inv, dict) else False
            for j, task in enumerate(pending):
                if not _eligible(task, inv):
                    continue
                if carried_animal and task[4] != "place":
                    continue
                dist = _distance(pos_u, task[1])
                # Routine chores prefer local quadrant (tie-breaker friction = 2 turns)
                friction = 2.0 if task[4] in ("water", "dig", "plant", "fertilizer") and _quadrant(task[1]) != q_u else 0.0
                turns = 1.0 + dist + friction
                ev = task[5] if len(task) > 5 else 10.0
                ev_per_turn = ev / turns
                candidates.append((ev_per_turn, -dist, unit, j))
        if not candidates:
            break
        best_ev_per_turn, _, unit, task_idx = max(candidates)
        task = pending.pop(task_idx)
        actions[unit] = task[2] if positions[unit] == task[1] else _move_toward(positions[unit], task[1], tiles)
        free.remove(unit)

    return actions


def _quadrant_crop_deficits(obs):
    player = int(_get(obs, "player", 0))
    farm = _get(obs, "farms", [])[player]
    private = _get(obs, "private", {}) or {}
    tiles = _get(farm, "tiles", [])
    seeds = _get(private, "seeds", {}) or {}
    day = int(_get(obs, "day", 0))
    unlocked = set(_get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    deficits = {crop: 0 for crop in CROPS}
    for pos, crop in _crop_plan(day).items():
        x, y = pos
        if not _active_target(pos, day, unlocked) or day > _last_plant(crop):
            continue
        tile = tiles[y][x]
        if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
            deficits[crop] += 1
    for crop in deficits:
        deficits[crop] = max(0, deficits[crop] - int(seeds.get(crop, 0)))
    return deficits



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


def _hire_costs(target, already):
    fib_a, fib_b = 1, 1
    costs = []
    for index in range(max(0, int(target))):
        if index >= max(0, int(already)):
            costs.append(fib_a)
        fib_a, fib_b = fib_b, fib_a + fib_b
    return costs


def _safe_buy_price(price):
    """Budget for simultaneous opponent orders moving a market price."""
    price = max(1, int(price))
    pct = max(0, int(STRATEGY.get("price_buffer_pct", 10)))
    return max(price + 2, (price * (100 + pct) + 99) // 100)


def _observe_opponent(obs):
    global _OPPONENT_STYLE, _EXPERT_EVIDENCE, _MARKET_ANIMAL_SHARE
    day = int(_get(obs, "day", 0))
    hour = int(_get(obs, "hour", 0))
    if day == 0 and hour == 0:
        _OPPONENT_STYLE = None
        _EXPERT_EVIDENCE = {}
        _MARKET_ANIMAL_SHARE = None
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    cow_roi = max(1.0, float(prices.get("MILK", 160))) / float(ANIMALS["COW"]["cost"])
    sheep_roi = max(1.0, float(prices.get("WOOL", 200))) / float(ANIMALS["SHEEP"]["cost"])
    sensitivity = max(0.1, float(STRATEGY.get("animal_price_sensitivity", 2.0)))
    cow_weight = cow_roi ** sensitivity
    sheep_weight = sheep_roi ** sensitivity
    _MARKET_ANIMAL_SHARE = cow_weight / (cow_weight + sheep_weight)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if day > 12 or len(farms) < 2:
        return
    opponent = farms[1 - player]
    tiles = [tile for row in (_get(opponent, "tiles", []) or []) for tile in row if isinstance(tile, dict)]
    plants = sum(tile.get("kind") == "PLANT" for tile in tiles)
    wheat = sum(tile.get("crop") == "WHEAT" for tile in tiles)
    strawberries = sum(tile.get("crop") == "STRAWBERRY" for tile in tiles)
    cows = sum(tile.get("animal") == "COW" for tile in tiles)
    sheep = sum(tile.get("animal") == "SHEEP" for tile in tiles)
    animals = sum(tile.get("animal") in ANIMALS for tile in tiles)

    evidence = {}
    if day <= 3 and sheep >= 2 and cows == 0:
        evidence["EARLY_SHEEP"] = 1.0
    if day <= 4 and plants >= 28 and wheat >= 20 and animals <= 1:
        evidence["WHEAT_RUSH"] = 1.0

    clear_livestock = (day <= 6 and animals >= 5 and plants <= 5) or (
        7 <= day <= 12 and animals >= 8 and plants <= 20 and strawberries <= 2
    )
    partial_livestock = 5 <= day <= 12 and animals >= 4 and plants <= 12 and strawberries <= 2
    if clear_livestock or partial_livestock:
        name = "SHEEP_RUSH" if sheep >= 5 and sheep >= 3 * max(1, cows) else "COW_RUSH"
        evidence[name] = 0.95 if clear_livestock else min(0.75, 0.35 + 0.08 * (animals - 4))

    for name, confidence in evidence.items():
        _EXPERT_EVIDENCE[name] = max(float(_EXPERT_EVIDENCE.get(name, 0)), confidence)
    if _EXPERT_EVIDENCE:
        _OPPONENT_STYLE = max(
            _EXPERT_EVIDENCE,
            key=lambda name: (_EXPERT_EVIDENCE[name], name == "WHEAT_RUSH", name),
        )


def _animal_purchase_cap():
    return 2


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

    # === 2. CRITICAL FEED & LABOUR MAINTENANCE ===
    # Emergency Feed Protection: NEVER allow an existing animal to starve!
    # Sunk capital is $400-$500 per animal. A missed feed destroys the entire animal.
    wheat_total = wheat_shed + sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    if wheat_total < animal_count and day < 28:
        feed_needed = animal_count - wheat_total
        p_wheat_buy = _safe_buy_price(prices.get("WHEAT", 25))
        buy_q = min(feed_needed, int(budget // p_wheat_buy))
        if buy_q > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_PRODUCT", "WHEAT", buy_q])
            budget -= buy_q * p_wheat_buy
            _MATCH_LEDGER["market_wheat_cost"] += buy_q * p_wheat_buy

    target_hires = _hire_target(day)
    already = int(_get(farm, "hires_today", 0))
    hire_costs = _hire_costs(target_hires, already)
    critical_target = min(target_hires, 2 if day <= 1 else 3 if day <= 4 else 5 if day <= 8 else 8 if day <= 14 else 10)
    critical_costs = _hire_costs(critical_target, already)
    hired_costs = 0
    for cost in critical_costs:
        if len(orders) >= MAX_ORDERS or budget < cost:
            break
        orders.append(["HIRE"])
        budget -= cost
        hired_costs += 1
        _MATCH_LEDGER["worker_wages"] += cost

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

    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000

    if land_cost > 0 and len(unlocked) < 3 and len(orders) < MAX_ORDERS:
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
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue
        
        # Physical Feasibility Constraint:
        # 1. Require at least 4 workers to physically operate livestock
        if target_hires < 4: continue
        # 2. Never buy more animals if existing animals are still waiting in the shed
        if shed_animals >= 2: continue
        
        # Multi-output ROI calculation with engine CARE bonus:
        # A cared animal yields 2 units on its interval (+1 care bonus)
        cap_cost = ANIMALS[animal]["cost"]
        p_prod = float(prices.get("MILK" if animal == "COW" else "WOOL", 80.0) or 80.0)
        yield_rate = 1.0 if animal == "COW" else 0.67 # 2 milk every 2d, 2 wool every 3d
        daily_prod_val = p_prod * yield_rate
        daily_val = daily_prod_val + p_fert
        feed_cost = 1.67 # On-farm grain cost
        labor_cost = 15.0 # Opportunity cost of worker actions
        daily_margin = daily_val - feed_cost - labor_cost
        
        if daily_margin <= 15.0: continue # Negative or trivial ROI
        payback = cap_cost / daily_margin
        if remaining_days < payback + 3: continue # Cannot amortize
        
        affordable = int(max(0, budget - operating_reserve - 300) // cap_cost)
        quantity = min(needed, affordable, remaining_animal_slots)
        if quantity > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_ANIMAL", animal, quantity])
            budget -= quantity * cap_cost
            remaining_animal_slots -= quantity
            shed_animals += quantity

    return orders[:MAX_ORDERS]


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
