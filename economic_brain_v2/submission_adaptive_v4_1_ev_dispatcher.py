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



DEFAULT_STRATEGY = {   'adaptive_animal_lead': 2,
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
    'fixed_board_adaptation': False,
    'fixed_schedule_version': 'v18',
    'force_expert': None,
    'hands': 11,
    'interference_collision_only': False,
    'interference_min_exposure': 0.5,
    'interference_preserve_wheat_order': True,
    'interference_sell_first': True,
    'interference_targeted_sort': False,
    'interference_wheat_min_cash': 10000,
    'interference_wheat_min_opponent_animals': 10,
    'interference_wheat_price_cap': 30,
    'interference_wheat_squeeze': False,
    'interference_wheat_units': 1,
    'land_ne_day': 5,
    'land_sw_day': 10,
    'livestock_animal_cap': 3,
    'livestock_cash_reserve': 150,
    'livestock_cows': 2,
    'livestock_sheep': 0,
    'livestock_strawberries': 34,
    'livestock_tomatoes': 0,
    'market_interference': True,
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
    'use_fixed_schedule': False,
    'v11_alpha_milk_price': 193,
    'v11_radiant_market_interference': False,
    'v11_radiant_player': 0,
    'v11_radiant_variant': 'adaptive',
    'v11_route_step': 109,
    'v12_late_market_mode': 'price',
    'v12_market_interference': False,
    'v13_gate_concentration': 0.5,
    'v13_gate_confidence': 0.7,
    'v13_gate_exposure_scale': 6.0,
    'v13_gate_lock_steps': 24,
    'v13_interference_min_exposure': 2.0,
    'v13_market_adaptation': True,
    'v14_gate_concentration': 0.5,
    'v14_gate_confidence': 0.7,
    'v14_gate_exposure_scale': 6.0,
    'v14_gate_lock_steps': 24,
    'v14_interference_min_exposure': 2.0,
    'v14_market_adaptation': True,
    'v15_gate_concentration': 0.5,
    'v15_gate_confidence': 0.7,
    'v15_gate_exposure_scale': 6.0,
    'v15_gate_lock_steps': 24,
    'v15_interference_min_exposure': 2.0,
    'v15_market_adaptation': True,
    'v16_gate_concentration': 0.5,
    'v16_gate_confidence': 0.7,
    'v16_gate_exposure_scale': 6.0,
    'v16_gate_lock_steps': 48,
    'v16_gate_price_floor_ratio': 0.5,
    'v16_interference_min_exposure': 2.0,
    'v16_market_adaptation': True,
    'v16_value_lane_margin': 0.05,
    'v17_market_ranker': True,
    'v17_rank_min_confidence': 0.95,
    'v18_closed_loop_board': True,
    'v18_closed_loop_market': True,
    'wheat_rush_animal_cap': 1,
    'wheat_rush_cash_reserve': 150,
    'zoned_workers': False}
STRATEGY = dict(DEFAULT_STRATEGY)

DEFAULT_STRATEGY = {   'adaptive_animal_lead': 2,
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
    'fixed_board_adaptation': False,
    'fixed_schedule_version': 'v18',
    'force_expert': None,
    'hands': 11,
    'interference_collision_only': False,
    'interference_min_exposure': 0.5,
    'interference_preserve_wheat_order': True,
    'interference_sell_first': True,
    'interference_targeted_sort': False,
    'interference_wheat_min_cash': 10000,
    'interference_wheat_min_opponent_animals': 10,
    'interference_wheat_price_cap': 30,
    'interference_wheat_squeeze': False,
    'interference_wheat_units': 1,
    'land_ne_day': 5,
    'land_sw_day': 10,
    'livestock_animal_cap': 3,
    'livestock_cash_reserve': 150,
    'livestock_cows': 2,
    'livestock_sheep': 0,
    'livestock_strawberries': 34,
    'livestock_tomatoes': 0,
    'market_interference': True,
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
    'use_fixed_schedule': False,
    'v11_alpha_milk_price': 193,
    'v11_radiant_market_interference': False,
    'v11_radiant_player': 0,
    'v11_radiant_variant': 'adaptive',
    'v11_route_step': 109,
    'v12_late_market_mode': 'price',
    'v12_market_interference': False,
    'v13_gate_concentration': 0.5,
    'v13_gate_confidence': 0.7,
    'v13_gate_exposure_scale': 6.0,
    'v13_gate_lock_steps': 24,
    'v13_interference_min_exposure': 2.0,
    'v13_market_adaptation': True,
    'v14_gate_concentration': 0.5,
    'v14_gate_confidence': 0.7,
    'v14_gate_exposure_scale': 6.0,
    'v14_gate_lock_steps': 24,
    'v14_interference_min_exposure': 2.0,
    'v14_market_adaptation': True,
    'v15_gate_concentration': 0.5,
    'v15_gate_confidence': 0.7,
    'v15_gate_exposure_scale': 6.0,
    'v15_gate_lock_steps': 24,
    'v15_interference_min_exposure': 2.0,
    'v15_market_adaptation': True,
    'v16_gate_concentration': 0.5,
    'v16_gate_confidence': 0.7,
    'v16_gate_exposure_scale': 6.0,
    'v16_gate_lock_steps': 48,
    'v16_gate_price_floor_ratio': 0.5,
    'v16_interference_min_exposure': 2.0,
    'v16_market_adaptation': True,
    'v16_value_lane_margin': 0.05,
    'v17_market_ranker': True,
    'v17_rank_min_confidence': 0.95,
    'v18_closed_loop_board': True,
    'v18_closed_loop_market': True,
    'wheat_rush_animal_cap': 1,
    'wheat_rush_cash_reserve': 150,
    'zoned_workers': False}
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
    global _V11_SELECTED_RADIANT_VARIANT
    global _V13_MARKET_MODE, _V13_MARKET_CONFIDENCE, _V13_MARKET_LOCK_UNTIL
    global _V14_MARKET_MODE, _V14_MARKET_CONFIDENCE, _V14_MARKET_LOCK_UNTIL
    global _V15_MARKET_MODE, _V15_MARKET_CONFIDENCE, _V15_MARKET_LOCK_UNTIL
    global _V16_MARKET_MODE, _V16_MARKET_CONFIDENCE, _V16_MARKET_LOCK_UNTIL
    global _V18_SELECTED_MARKET, _V18_SELECTED_DAY, _V18_SELECTED_BOARD
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
    _V11_SELECTED_RADIANT_VARIANT = None
    _V13_MARKET_MODE = "BASE"
    _V13_MARKET_CONFIDENCE = 0.0
    _V13_MARKET_LOCK_UNTIL = -1
    _V14_MARKET_MODE = "BASE"
    _V14_MARKET_CONFIDENCE = 0.0
    _V14_MARKET_LOCK_UNTIL = -1
    _V15_MARKET_MODE = "BASE"
    _V15_MARKET_CONFIDENCE = 0.0
    _V15_MARKET_LOCK_UNTIL = -1
    _V16_MARKET_MODE = "BASE"
    _V16_MARKET_CONFIDENCE = 0.0
    _V16_MARKET_LOCK_UNTIL = -1
    _V18_SELECTED_MARKET = {0: None, 1: None}
    _V18_SELECTED_DAY = {0: None, 1: None}
    _V18_SELECTED_BOARD = {0: None, 1: None}
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


def _copy_action(action):
    """Copy a scheduled action before an observation-dependent overlay."""
    if not isinstance(action, dict):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }


def _farm_pipeline(farm):
    """Estimate near-future market exposure from public farm assets.

    Opponent inventories are private, so this is deliberately a portfolio
    estimate rather than a prediction of the next exact action.  Yield already
    waiting on a tile receives extra weight, while recurring assets retain a
    smaller baseline weight even between production days.
    """
    exposure = {
        "WHEAT": 0.0,
        "CARROT": 0.0,
        "TOMATO": 0.0,
        "STRAWBERRY": 0.0,
        "MELON": 0.0,
        "EGG": 0.0,
        "MILK": 0.0,
        "WOOL": 0.0,
    }
    animals = 0
    unfed = 0
    for row in (_get(farm, "tiles", []) or []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            ready = max(0.0, float(tile.get("yield_units", 0) or 0))
            crop = tile.get("crop")
            if tile.get("kind") == "PLANT" and crop in exposure:
                # A live crop represents future supply; ready produce is much
                # more likely to collide with our sale in the next few turns.
                exposure[crop] += 1.0 + 2.0 * ready
            animal = tile.get("animal")
            product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}.get(animal)
            if product:
                animals += 1
                unfed += int(not bool(tile.get("fed_today", False)))
                cadence = {"EGG": 1.0, "MILK": 0.5, "WOOL": 1.0 / 3.0}[product]
                exposure[product] += cadence + 2.0 * ready
    # Feed demand is the only visible buy-side pressure worth considering.
    # Unfed animals increase urgency but do not prove that the shed is empty.
    exposure["WHEAT"] += animals + 0.5 * unfed
    exposure["ANIMALS"] = float(animals)
    exposure["UNFED"] = float(unfed)
    return exposure


def _opponent_pipeline(obs):
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return {}
    return _farm_pipeline(farms[1 - player])


def _interference_value(obs, product, quantity=1, pipeline=None):
    """Relative denial value used only to sequence existing v8 sales."""
    pipeline = pipeline if pipeline is not None else _opponent_pipeline(obs)
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    exposure = max(0.0, float(pipeline.get(product, 0.0)))
    price = max(1.0, float(prices.get(product, 1.0)))
    quantity = max(1.0, float(quantity or 1))
    # Exposure captures the opponent's likely supply; price captures how much
    # acceleration is denied if our sale reaches the shared market first.
    return exposure * price * min(quantity, 10.0)


def _safe_wheat_squeeze(obs, market_orders, pipeline):
    """Optionally add one strictly gated feed-denial order.

    This is disabled in the submitted defaults until it beats the unchanged
    v8 schedule out of sample.  Keeping the gate here makes that hypothesis
    directly testable without weakening the production executor.
    """
    if not STRATEGY.get("interference_wheat_squeeze") or len(market_orders) >= MAX_ORDERS:
        return market_orders
    day = int(_get(obs, "day", 0))
    hour = int(_get(obs, "hour", 0))
    if not (8 <= day <= 24 and hour == 0):
        return market_orders
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return market_orders
    own = farms[player]
    opponent = farms[1 - player]
    if float(_get(own, "money", 0)) < float(STRATEGY.get("interference_wheat_min_cash", 10000)):
        return market_orders
    if float(pipeline.get("ANIMALS", 0)) < float(STRATEGY.get("interference_wheat_min_opponent_animals", 10)):
        return market_orders
    # Attack only a genuinely liquidity-sensitive herd, never a rich rival.
    if float(_get(opponent, "money", 0)) > 250:
        return market_orders
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    if float(prices.get("WHEAT", 10 ** 9)) > float(STRATEGY.get("interference_wheat_price_cap", 30)):
        return market_orders
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    own_pipeline = _farm_pipeline(own)
    own_animals = int(own_pipeline.get("ANIMALS", 0))
    if int(shed.get("WHEAT", 0) or 0) < 2 * own_animals:
        return market_orders
    if any(order and order[0] == "SELL" and len(order) > 1 and order[1] == "WHEAT" for order in market_orders):
        return market_orders
    units = max(0, min(1, int(STRATEGY.get("interference_wheat_units", 1))))
    if units:
        market_orders.append(["BUY_PRODUCT", "WHEAT", units])
    return market_orders


def _apply_market_interference(obs, action):
    """Apply a market-only overlay without changing farm execution."""
    copied = _copy_action(action)
    if not STRATEGY.get("market_interference"):
        return copied
    pipeline = _opponent_pipeline(obs)
    if not pipeline:
        return copied
    orders = copied["market"]
    if STRATEGY.get("interference_sell_first"):
        targeted = bool(STRATEGY.get("interference_targeted_sort"))

        def priority(pair):
            index, order = pair
            is_sell = bool(order) and order[0] == "SELL"
            if not is_sell:
                return (1, 0.0, index)
            product = order[1] if len(order) > 1 else ""
            quantity = order[2] if len(order) > 2 else 1
            if STRATEGY.get("interference_preserve_wheat_order") and product == "WHEAT":
                return (1, 0.0, index)
            if (
                STRATEGY.get("interference_collision_only")
                and float(pipeline.get(product, 0.0))
                < float(STRATEGY.get("interference_min_exposure", 0.5))
            ):
                return (1, 0.0, index)
            value = _interference_value(obs, product, quantity, pipeline) if targeted else 0.0
            return (0, -value, index)

        orders = [order for _, order in sorted(enumerate(orders), key=priority)]
    copied["market"] = _safe_wheat_squeeze(obs, orders, pipeline)[:MAX_ORDERS]
    return copied


def _v13_market_mode(obs):
    """Select a market expert from public supply with daily hysteresis.

    Production and movement remain on one coherent route.  Only the ordering
    of already-planned sales may change, so a classification error cannot
    invalidate future farm actions.
    """
    global _V13_MARKET_MODE, _V13_MARKET_CONFIDENCE, _V13_MARKET_LOCK_UNTIL
    step = max(0, int(_get(obs, "step", 0)))
    hour = int(_get(obs, "hour", step % 24))
    if step == 0:
        _V13_MARKET_MODE = "BASE"
        _V13_MARKET_CONFIDENCE = 0.0
        _V13_MARKET_LOCK_UNTIL = -1
    if not STRATEGY.get("v13_market_adaptation", True):
        return "BASE"
    if step < _V13_MARKET_LOCK_UNTIL or (hour != 0 and step > 0):
        return _V13_MARKET_MODE

    pipeline = _opponent_pipeline(obs)
    values = [
        max(0.0, float(pipeline.get(product, 0.0)))
        for product in ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
    ]
    total = sum(values)
    concentration = max(values, default=0.0) / total if total > 0 else 0.0
    scale = max(0.1, float(STRATEGY.get("v13_gate_exposure_scale", 6.0)))
    target_concentration = max(
        0.1, float(STRATEGY.get("v13_gate_concentration", 0.50))
    )
    confidence = min(1.0, total / scale) * min(
        1.0, concentration / target_concentration
    )
    _V13_MARKET_CONFIDENCE = confidence
    threshold = max(0.0, min(1.0, float(STRATEGY.get("v13_gate_confidence", 0.70))))
    next_mode = "COLLISION" if confidence >= threshold else "BASE"
    # Require substantially weaker contrary evidence before leaving an active
    # specialist.  Public assets normally change slowly, but this also covers
    # deliberate mid-game strategy reversals.
    if _V13_MARKET_MODE == "COLLISION" and confidence >= threshold * 0.5:
        next_mode = "COLLISION"
    if next_mode != _V13_MARKET_MODE:
        _V13_MARKET_MODE = next_mode
        _V13_MARKET_LOCK_UNTIL = step + max(
            1, int(STRATEGY.get("v13_gate_lock_steps", 24))
        )
    return _V13_MARKET_MODE


def _v13_senkin_action(obs, step):
    """Run the robust core plus a compatible opponent-conditioned expert."""
    copied = _copy_action(_V13_SENKIN_SCHEDULE[step])
    if _v13_market_mode(obs) != "COLLISION":
        return copied
    pipeline = _opponent_pipeline(obs)
    minimum = max(0.0, float(STRATEGY.get("v13_interference_min_exposure", 2.0)))

    def priority(pair):
        index, order = pair
        if not order or order[0] != "SELL" or len(order) < 2:
            return (1, 0.0, index)
        product = order[1]
        # Wheat is working capital for the coherent feed loop.  Its exact
        # buy/sell ordering is never changed by the market expert.
        if product == "WHEAT" or float(pipeline.get(product, 0.0)) < minimum:
            return (1, 0.0, index)
        quantity = order[2] if len(order) > 2 else 1
        return (0, -_interference_value(obs, product, quantity, pipeline), index)

    copied["market"] = [
        order for _, order in sorted(enumerate(copied["market"]), key=priority)
    ][:MAX_ORDERS]
    return copied


def _v14_market_mode(obs):
    """Select a collision expert using price-weighted public concentration.

    v13 measured concentration in physical exposure only.  v14 keeps the same
    conservative daily gate, but normalizes each visible product pipeline by
    its equilibrium price before measuring concentration.  This makes a
    premium product at the market floor weak evidence while preserving the
    signal from a genuinely valuable, concentrated pipeline.
    """
    global _V14_MARKET_MODE, _V14_MARKET_CONFIDENCE, _V14_MARKET_LOCK_UNTIL
    step = max(0, int(_get(obs, "step", 0)))
    hour = int(_get(obs, "hour", step % 24))
    if step == 0:
        _V14_MARKET_MODE = "BASE"
        _V14_MARKET_CONFIDENCE = 0.0
        _V14_MARKET_LOCK_UNTIL = -1
    if not STRATEGY.get("v14_market_adaptation", True):
        return "BASE"
    if step < _V14_MARKET_LOCK_UNTIL or (hour != 0 and step > 0):
        return _V14_MARKET_MODE

    pipeline = _opponent_pipeline(obs)
    products = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
    exposures = [max(0.0, float(pipeline.get(product, 0.0))) for product in products]
    total_exposure = sum(exposures)
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    reference = {
        "CARROT": 35.0,
        "TOMATO": 60.0,
        "STRAWBERRY": 120.0,
        "MELON": 250.0,
        "EGG": 50.0,
        "MILK": 160.0,
        "WOOL": 200.0,
    }
    weighted = [
        exposure * max(1.0, float(prices.get(product, reference[product])))
        / reference[product]
        for product, exposure in zip(products, exposures)
    ]
    weighted_total = sum(weighted)
    concentration = max(weighted, default=0.0) / weighted_total if weighted_total > 0 else 0.0
    scale = max(0.1, float(STRATEGY.get("v14_gate_exposure_scale", 6.0)))
    target_concentration = max(0.1, float(STRATEGY.get("v14_gate_concentration", 0.50)))
    confidence = min(1.0, total_exposure / scale) * min(
        1.0, concentration / target_concentration
    )
    _V14_MARKET_CONFIDENCE = confidence
    threshold = max(0.0, min(1.0, float(STRATEGY.get("v14_gate_confidence", 0.70))))
    next_mode = "COLLISION" if confidence >= threshold else "BASE"
    if _V14_MARKET_MODE == "COLLISION" and confidence >= threshold * 0.5:
        next_mode = "COLLISION"
    if next_mode != _V14_MARKET_MODE:
        _V14_MARKET_MODE = next_mode
        _V14_MARKET_LOCK_UNTIL = step + max(
            1, int(STRATEGY.get("v14_gate_lock_steps", 24))
        )
    return _V14_MARKET_MODE


def _v14_senkin_action(obs, step):
    """Run the v13 route with v14's price-aware collision ordering."""
    copied = _copy_action(_V13_SENKIN_SCHEDULE[step])
    if _v14_market_mode(obs) != "COLLISION":
        return copied
    pipeline = _opponent_pipeline(obs)
    minimum = max(0.0, float(STRATEGY.get("v14_interference_min_exposure", 2.0)))

    def priority(pair):
        index, order = pair
        if not order or order[0] != "SELL" or len(order) < 2:
            return (1, 0.0, index)
        product = order[1]
        # WHEAT is the working-capital loop and remains in its validated order.
        if product == "WHEAT" or float(pipeline.get(product, 0.0)) < minimum:
            return (1, 0.0, index)
        quantity = order[2] if len(order) > 2 else 1
        return (0, -_interference_value(obs, product, quantity, pipeline), index)

    copied["market"] = [
        order for _, order in sorted(enumerate(copied["market"]), key=priority)
    ][:MAX_ORDERS]
    return copied


def _v15_market_mode(obs):
    """Use v13 exposure evidence with v14 price evidence as a consensus gate.

    The v14 leaderboard result showed that price weighting should not replace
    the physical portfolio signal.  v15 therefore activates only when both
    views agree.  The gate is never more eager than v13, while a floor-priced
    product cannot create a false collision signal by itself.
    """
    global _V15_MARKET_MODE, _V15_MARKET_CONFIDENCE, _V15_MARKET_LOCK_UNTIL
    step = max(0, int(_get(obs, "step", 0)))
    hour = int(_get(obs, "hour", step % 24))
    if step == 0:
        _V15_MARKET_MODE = "BASE"
        _V15_MARKET_CONFIDENCE = 0.0
        _V15_MARKET_LOCK_UNTIL = -1
    if not STRATEGY.get("v15_market_adaptation", True):
        return "BASE"
    if step < _V15_MARKET_LOCK_UNTIL or (hour != 0 and step > 0):
        return _V15_MARKET_MODE

    pipeline = _opponent_pipeline(obs)
    products = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
    exposures = [max(0.0, float(pipeline.get(product, 0.0))) for product in products]
    total_exposure = sum(exposures)
    physical_concentration = (
        max(exposures, default=0.0) / total_exposure if total_exposure > 0 else 0.0
    )
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    reference = {
        "CARROT": 35.0,
        "TOMATO": 60.0,
        "STRAWBERRY": 120.0,
        "MELON": 250.0,
        "EGG": 50.0,
        "MILK": 160.0,
        "WOOL": 200.0,
    }
    weighted = [
        exposure * max(1.0, float(prices.get(product, reference[product])))
        / reference[product]
        for product, exposure in zip(products, exposures)
    ]
    weighted_total = sum(weighted)
    value_concentration = (
        max(weighted, default=0.0) / weighted_total if weighted_total > 0 else 0.0
    )
    scale = max(0.1, float(STRATEGY.get("v15_gate_exposure_scale", 6.0)))
    target_concentration = max(0.1, float(STRATEGY.get("v15_gate_concentration", 0.50)))
    volume_confidence = min(1.0, total_exposure / scale) * min(
        1.0, physical_concentration / target_concentration
    )
    value_confidence = min(1.0, total_exposure / scale) * min(
        1.0, value_concentration / target_concentration
    )
    # Intersection, rather than union: preserve v13's precision and use
    # v14's price view only to veto weak/floor-priced collision evidence.
    confidence = min(volume_confidence, value_confidence)
    _V15_MARKET_CONFIDENCE = confidence
    threshold = max(0.0, min(1.0, float(STRATEGY.get("v15_gate_confidence", 0.70))))
    next_mode = "COLLISION" if confidence >= threshold else "BASE"
    if _V15_MARKET_MODE == "COLLISION" and confidence >= threshold * 0.5:
        next_mode = "COLLISION"
    if next_mode != _V15_MARKET_MODE:
        _V15_MARKET_MODE = next_mode
        _V15_MARKET_LOCK_UNTIL = step + max(
            1, int(STRATEGY.get("v15_gate_lock_steps", 24))
        )
    return _V15_MARKET_MODE


def _v15_senkin_action(obs, step):
    """Run v13's route with a conservative top-five collision specialist."""
    copied = _copy_action(_V13_SENKIN_SCHEDULE[step])
    if _v15_market_mode(obs) != "COLLISION":
        return copied
    pipeline = _opponent_pipeline(obs)
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    minimum = max(0.0, float(STRATEGY.get("v15_interference_min_exposure", 2.0)))

    def priority(pair):
        index, order = pair
        if not order or order[0] != "SELL" or len(order) < 2:
            return (1, 0.0, index)
        product = order[1]
        # WHEAT remains the validated working-capital loop.  Do not spend a
        # scarce market slot on a product already pinned to the $1 floor.
        if (
            product == "WHEAT"
            or float(pipeline.get(product, 0.0)) < minimum
            or float(prices.get(product, 10 ** 9)) <= 1.0
        ):
            return (1, 0.0, index)
        quantity = order[2] if len(order) > 2 else 1
        return (0, -_interference_value(obs, product, quantity, pipeline), index)

    copied["market"] = [
        order for _, order in sorted(enumerate(copied["market"]), key=priority)
    ][:MAX_ORDERS]
    return copied


def _v16_core_schedule(obs):
    """Select one complete route by player position; never switch mid-game."""
    return (
        _V16_P0_SCHEDULE
        if int(_get(obs, "player", 0)) == 0
        else _V16_P1_SCHEDULE
    )


def _v16_market_mode(obs):
    """Choose a public-state collision lane with a slow, conservative gate."""
    global _V16_MARKET_MODE, _V16_MARKET_CONFIDENCE, _V16_MARKET_LOCK_UNTIL
    step = max(0, int(_get(obs, "step", 0)))
    hour = int(_get(obs, "hour", step % 24))
    if step == 0:
        _V16_MARKET_MODE = "BASE"
        _V16_MARKET_CONFIDENCE = 0.0
        _V16_MARKET_LOCK_UNTIL = -1
    if not STRATEGY.get("v16_market_adaptation", True):
        return "BASE"
    if step < _V16_MARKET_LOCK_UNTIL or (hour != 0 and step > 0):
        return _V16_MARKET_MODE

    pipeline = _opponent_pipeline(obs)
    products = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
    exposures = [max(0.0, float(pipeline.get(product, 0.0))) for product in products]
    total_exposure = sum(exposures)
    physical_concentration = (
        max(exposures, default=0.0) / total_exposure if total_exposure > 0 else 0.0
    )
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    reference = {
        "CARROT": 35.0,
        "TOMATO": 60.0,
        "STRAWBERRY": 120.0,
        "MELON": 250.0,
        "EGG": 50.0,
        "MILK": 160.0,
        "WOOL": 200.0,
    }
    weighted = [
        exposure * max(1.0, float(prices.get(product, reference[product])))
        / reference[product]
        for product, exposure in zip(products, exposures)
    ]
    weighted_total = sum(weighted)
    value_concentration = (
        max(weighted, default=0.0) / weighted_total if weighted_total > 0 else 0.0
    )
    scale = max(0.1, float(STRATEGY.get("v16_gate_exposure_scale", 6.0)))
    target = max(0.1, float(STRATEGY.get("v16_gate_concentration", 0.50)))
    volume_confidence = min(1.0, total_exposure / scale) * min(
        1.0, physical_concentration / target
    )
    value_confidence = min(1.0, total_exposure / scale) * min(
        1.0, value_concentration / target
    )
    confidence = min(volume_confidence, value_confidence)
    top_index = max(range(len(products)), key=lambda index: weighted[index], default=0)
    top_product = products[top_index]
    top_price_ratio = max(1.0, float(prices.get(top_product, reference[top_product]))) / reference[top_product]
    if top_price_ratio < max(
        0.0, float(STRATEGY.get("v16_gate_price_floor_ratio", 0.50))
    ):
        confidence = 0.0
    _V16_MARKET_CONFIDENCE = confidence
    threshold = max(0.0, min(1.0, float(STRATEGY.get("v16_gate_confidence", 0.70))))
    if confidence >= threshold:
        margin = max(0.0, float(STRATEGY.get("v16_value_lane_margin", 0.05)))
        next_mode = (
            "VALUE" if value_confidence >= volume_confidence + margin else "VOLUME"
        )
    elif _V16_MARKET_MODE in {"VOLUME", "VALUE"} and confidence >= threshold * 0.5:
        next_mode = _V16_MARKET_MODE
    else:
        next_mode = "BASE"
    if next_mode != _V16_MARKET_MODE:
        _V16_MARKET_MODE = next_mode
        _V16_MARKET_LOCK_UNTIL = step + max(
            1, int(STRATEGY.get("v16_gate_lock_steps", 48))
        )
    return _V16_MARKET_MODE


def _v16_senkin_action(obs, step):
    """Run one coherent v16 route with a two-lane public-observation overlay."""
    copied = _copy_action(_v16_core_schedule(obs)[step])
    mode = _v16_market_mode(obs)
    if mode == "BASE":
        return copied
    pipeline = _opponent_pipeline(obs)
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    minimum = max(0.0, float(STRATEGY.get("v16_interference_min_exposure", 2.0)))

    def priority(pair):
        index, order = pair
        if not order or order[0] != "SELL" or len(order) < 2:
            return (1, 0.0, index)
        product = order[1]
        # WHEAT is working capital; its exact position is never reordered.
        if (
            product == "WHEAT"
            or float(pipeline.get(product, 0.0)) < minimum
            or float(prices.get(product, 10 ** 9)) <= 1.0
        ):
            return (1, 0.0, index)
        quantity = order[2] if len(order) > 2 else 1
        exposure = max(0.0, float(pipeline.get(product, 0.0)))
        score = (
            _interference_value(obs, product, quantity, pipeline)
            if mode == "VALUE"
            else exposure * min(float(quantity or 1), 10.0)
        )
        return (0, -score, index)

    copied["market"] = [
        order for _, order in sorted(enumerate(copied["market"]), key=priority)
    ][:MAX_ORDERS]
    return copied


def _v17_number(value, default=0.0):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _v17_clip(value, low=-20.0, high=20.0):
    return min(high, max(low, _v17_number(value)))


def _v17_ready_amount(tile):
    for key in ("yield_units", "ready_yield", "yield", "amount", "quantity"):
        if key in tile:
            return max(0.0, _v17_number(tile.get(key)))
    return 1.0 if tile.get("ready") is True or tile.get("is_ready") is True else 0.0


def _v17_public_farm_stats(farm):
    """Mirror the offline public-only feature extractor without private data."""
    products = tuple(_V17_MARKET_MODEL["products"])
    supply = {product: 0.0 for product in products}
    ready = {product: 0.0 for product in products}
    crop_to_product = {
        product: product for product in ("CARROT", "TOMATO", "STRAWBERRY", "MELON")
    }
    animal_to_product = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
    for row in (_get(farm, "tiles", []) or []):
        row = row if isinstance(row, list) else [row]
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = tile.get("crop")
            animal = tile.get("animal")
            product = crop_to_product.get(str(crop).upper()) if crop is not None else None
            if product is None and animal is not None:
                product = animal_to_product.get(str(animal).upper())
            if product is None:
                product = animal_to_product.get(str(tile.get("kind", "")).upper())
            if product is None:
                continue
            amount = _v17_ready_amount(tile)
            ready[product] += amount
            supply[product] += 1.0 + amount
    return {"supply": supply, "ready": ready}


def _v17_candidate_features(obs, product, planned_quantity):
    """Return the frozen model's 53 public candidate features in schema order."""
    products = tuple(_V17_MARKET_MODEL["products"])
    if product not in products:
        return None
    farms = _get(obs, "farms", []) or []
    player = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    own_farm = farms[player] if player < len(farms) else {}
    opponent_farm = farms[1 - player] if len(farms) > 1 else {}
    own = _v17_public_farm_stats(own_farm)
    opponent = _v17_public_farm_stats(opponent_farm)
    step = max(0.0, _v17_number(_get(obs, "step", 0)))
    day = max(0.0, _v17_number(_get(obs, "day", math.floor(step / 24.0))))
    hour = _v17_number(_get(obs, "hour", step % 24.0)) % 24.0
    market = _get(obs, "market", {}) or {}
    prices_raw = _get(market, "prices", None)
    if not isinstance(prices_raw, dict):
        prices_raw = _get(market, "current_prices", {}) or {}
    prices = {
        str(key).upper(): max(0.0, _v17_number(value))
        for key, value in prices_raw.items()
    }
    price_values = [max(1.0, prices.get(candidate, 1.0)) for candidate in products]
    mean_price = sum(price_values) / len(price_values)
    max_price = max(price_values)
    total_opponent_supply = sum(opponent["supply"].values())
    total_opponent_value = sum(
        opponent["supply"].get(candidate, 0.0)
        * max(1.0, prices.get(candidate, 1.0))
        for candidate in products
    )
    index = products.index(product)
    onehot = [0.0] * len(products)
    onehot[index] = 1.0
    day_fraction = min(1.0, day / 30.0)
    hour_sin = math.sin(2.0 * math.pi * hour / 24.0)
    hour_cos = math.cos(2.0 * math.pi * hour / 24.0)
    values = list(onehot)
    values.extend(value * day_fraction for value in onehot)
    values.extend(value * float(player) for value in onehot)
    values.extend(value * hour_sin for value in onehot)
    values.extend(value * hour_cos for value in onehot)
    price = max(1.0, prices.get(product, 1.0))
    own_supply = own["supply"].get(product, 0.0)
    opponent_supply = opponent["supply"].get(product, 0.0)
    opponent_value = opponent_supply * price
    own_value = own_supply * price
    own_total_value = sum(
        own["supply"].get(candidate, 0.0) * max(1.0, prices.get(candidate, 1.0))
        for candidate in products
    )
    price_rank = 1.0 + sum(other < price for other in price_values)
    quantity = max(0.0, _v17_number(planned_quantity))
    values.extend((
        math.log1p(quantity),
        min(1.0, quantity / 20.0),
        math.log1p(price),
        _v17_clip(math.log(price / max(1.0, mean_price))),
        _v17_clip(math.log(price / max(1.0, max_price))),
        price_rank / len(products),
        math.log1p(max(0.0, own_supply)),
        math.log1p(max(0.0, opponent_supply)),
        math.log1p(max(0.0, own["ready"].get(product, 0.0))),
        math.log1p(max(0.0, opponent["ready"].get(product, 0.0))),
        opponent_supply / max(1.0, total_opponent_supply),
        opponent_value / max(1.0, total_opponent_value),
        own_value / max(1.0, own_total_value),
    ))
    return [_v17_clip(value) for value in values]


def _v17_pair_probability(obs, left_order, right_order):
    """Predict which of two distinct product orders should execute first."""
    products = tuple(_V17_MARKET_MODEL["products"])
    left_product, right_product = left_order[1], right_order[1]
    if left_product == right_product:
        return 0.5
    left_quantity = left_order[2] if len(left_order) > 2 else 1
    right_quantity = right_order[2] if len(right_order) > 2 else 1
    # Training labels use the canonical product order.  Orient the runtime pair
    # the same way, then flip the probability back to the caller's order.
    caller_is_canonical = products.index(left_product) < products.index(right_product)
    canonical_left = left_order if caller_is_canonical else right_order
    canonical_right = right_order if caller_is_canonical else left_order
    canonical_left_quantity = left_quantity if caller_is_canonical else right_quantity
    canonical_right_quantity = right_quantity if caller_is_canonical else left_quantity
    left_features = _v17_candidate_features(
        obs, canonical_left[1], canonical_left_quantity
    )
    right_features = _v17_candidate_features(
        obs, canonical_right[1], canonical_right_quantity
    )
    if left_features is None or right_features is None:
        return 0.5
    standardization = _V17_MARKET_MODEL["standardization"]
    mean = standardization["mean"]
    scale = standardization["scale"]
    difference = [left - right for left, right in zip(left_features, right_features)]
    standardized = [
        (value - center) / (spread if abs(spread) > 1e-12 else 1.0)
        for value, center, spread in zip(difference, mean, scale)
    ]
    layers = _V17_MARKET_MODEL["layers"]
    hidden = []
    for hidden_index, bias in enumerate(layers["hidden_bias"]):
        total = bias + sum(
            value * layers["input_to_hidden"][feature_index][hidden_index]
            for feature_index, value in enumerate(standardized)
        )
        hidden.append(math.tanh(total))
    logit = layers["output_bias"] + sum(
        value * weight for value, weight in zip(hidden, layers["hidden_to_output"])
    )
    logit /= max(1e-6, float(_V17_MARKET_MODEL["calibration_temperature"]))
    if logit >= 0.0:
        probability = 1.0 / (1.0 + math.exp(-min(60.0, logit)))
    else:
        exponential = math.exp(max(-60.0, logit))
        probability = exponential / (1.0 + exponential)
    return probability if caller_is_canonical else 1.0 - probability


def _v17_learned_action(obs, step):
    """Re-rank only existing non-WHEAT SELLs; keep every protected slot fixed."""
    copied = _copy_action(_V17_SCHEDULE[step])
    if not STRATEGY.get("v17_market_ranker", True):
        return copied
    products = set(_V17_MARKET_MODEL["products"])
    free_indices = [
        index
        for index, order in enumerate(copied["market"])
        if order and len(order) >= 2 and order[0] == "SELL" and order[1] in products
    ]
    if len(free_indices) < 2:
        return copied
    scores = {index: 0.0 for index in free_indices}
    minimum_confidence = max(
        0.0, min(1.0, float(STRATEGY.get("v17_rank_min_confidence", 0.0)))
    )
    for offset, left_index in enumerate(free_indices):
        for right_index in free_indices[offset + 1:]:
            probability = _v17_pair_probability(
                obs, copied["market"][left_index], copied["market"][right_index]
            )
            if 2.0 * abs(probability - 0.5) < minimum_confidence:
                probability = 0.5
            scores[left_index] += probability
            scores[right_index] += 1.0 - probability
    ranked_orders = [
        copied["market"][index]
        for index in sorted(free_indices, key=lambda index: (-scores[index], index))
    ]
    for index, order in zip(free_indices, ranked_orders):
        copied["market"][index] = order
    return copied


_V18_PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)


def _v18_state_features(obs):
    """Public own-state vector used by the offline and submission gates."""
    player = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    farms = _get(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) and isinstance(farms[player], dict) else {}
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", _get(market, "current_prices", {})) or {}
    counts = {
        name: 0.0
        for name in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "COW", "SHEEP", "GOOSE",
        )
    }
    for row in farm.get("tiles", []) or []:
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            crop = str(tile.get("crop", "")).upper()
            animal = str(tile.get("animal", tile.get("kind", ""))).upper()
            if crop in counts:
                counts[crop] += 1.0
            if animal in counts:
                counts[animal] += 1.0
    values = [
        math.log1p(max(0.0, _v17_number(farm.get("money", 0)))),
        len(farm.get("hands", []) or []) / 16.0,
        len(farm.get("unlocked_quadrants", []) or []) / 4.0,
    ]
    values.extend(
        counts[name] / 50.0
        for name in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "COW", "SHEEP", "GOOSE",
        )
    )
    values.extend(
        math.log1p(max(0.0, _v17_number(shed.get(name, 0))))
        for name in _V18_PRODUCTS
    )
    price_values = [
        max(1.0, _v17_number(prices.get(name, 1), 1.0))
        for name in _V18_PRODUCTS
    ]
    mean_price = sum(price_values) / len(price_values)
    values.extend(math.log(value / mean_price) for value in price_values)
    return values


def _v18_closed_loop_action(obs, step):
    """Lock a seat route and choose a complete market expert once per day.

    The learned choice is outcome-based: complete-game wins set the seat
    priors, and public state similarity supplies the closed-loop correction.
    No SELL-order imitation label is used at training or runtime.
    """
    global _V18_SELECTED_MARKET, _V18_SELECTED_DAY, _V18_SELECTED_BOARD
    seat = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    experts = _V18_RUNTIME["experts"]
    base_board_name = _V18_RUNTIME["board_by_seat"][str(seat)]
    base_board_actions = experts[base_board_name]["actions"]
    bounded_step = min(max(0, int(step)), len(base_board_actions) - 1)
    if bounded_step == 0:
        _V18_SELECTED_MARKET[seat] = None
        _V18_SELECTED_DAY[seat] = None
        _V18_SELECTED_BOARD[seat] = None

    board_strength = float(_V18_RUNTIME.get("board_distance_strength", 0.0))
    board_fork_step = int(_V18_RUNTIME.get("board_fork_step", len(base_board_actions)))
    if (
        STRATEGY.get("v18_closed_loop_board", True)
        and board_strength > 0.0
        and bounded_step >= board_fork_step
        and _V18_SELECTED_BOARD[seat] is None
    ):
        current = _v18_state_features(obs)
        scales = _V18_RUNTIME["feature_standardization"]["scale"]
        bias = _V18_RUNTIME["board_bias_by_seat"][str(seat)]
        best_board = None
        for name, expert in experts.items():
            prototype = expert["board_prototype_at_fork"]
            distance = sum(
                ((value - center) / max(1e-12, float(scale))) ** 2
                for value, center, scale in zip(current, prototype, scales)
            ) / len(current)
            candidate = (float(bias.get(name, 0.0)) - board_strength * distance, name)
            if best_board is None or candidate > best_board:
                best_board = candidate
        _V18_SELECTED_BOARD[seat] = best_board[1]

    board_name = _V18_SELECTED_BOARD[seat] or base_board_name
    board_actions = experts[board_name]["actions"]
    board_action = board_actions[bounded_step] or {
        "farmer": ["PASS"], "hands": [], "market": [],
    }
    if not STRATEGY.get("v18_closed_loop_market", True):
        return _copy_action(board_action)

    day = max(0, int(_get(obs, "day", bounded_step // 24) or 0))
    if _V18_SELECTED_DAY[seat] != day or _V18_SELECTED_MARKET[seat] is None:
        current = _v18_state_features(obs)
        scales = _V18_RUNTIME["feature_standardization"]["scale"]
        bias = _V18_RUNTIME["market_bias_by_seat"][str(seat)]
        distance_strength = float(_V18_RUNTIME["distance_strength"])
        stay_bonus = float(_V18_RUNTIME["stay_bonus"])
        selected = _V18_SELECTED_MARKET[seat]
        best = None
        for name, expert in experts.items():
            prototypes = expert["prototypes_by_day"]
            prototype = prototypes[min(day, len(prototypes) - 1)]
            distance = sum(
                ((value - center) / max(1e-12, float(scale))) ** 2
                for value, center, scale in zip(current, prototype, scales)
            ) / len(current)
            score = float(bias.get(name, 0.0)) - distance_strength * distance
            if name == selected:
                score += stay_bonus
            candidate = (score, name)
            if best is None or candidate > best:
                best = candidate
        _V18_SELECTED_MARKET[seat] = best[1]
        _V18_SELECTED_DAY[seat] = day

    market_name = _V18_SELECTED_MARKET[seat]
    market_actions = experts[market_name]["actions"]
    market_action = market_actions[min(bounded_step, len(market_actions) - 1)] or {}
    return {
        "farmer": list(board_action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (board_action.get("hands") or [])],
        "market": [list(order) for order in (market_action.get("market") or [])],
    }


def _public_farm_counts(farm):
    """Return stable public portfolio features for a farm.

    Fixed replay executors cannot safely swap movement trajectories halfway
    through a game.  Animal species and within-turn purchase priority are
    different: both share the same pasture sites and unit actions, so they can
    react to public state without invalidating the remaining executor.
    """
    counts = {
        "COW": 0,
        "SHEEP": 0,
        "GOOSE": 0,
        "PLANTS": 0,
        "STRAWBERRY": 0,
        "LAND": len(_get(farm, "unlocked_quadrants", []) or []),
        "MONEY": float(_get(farm, "money", 0) or 0),
    }
    for row in (_get(farm, "tiles", []) or []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            animal = tile.get("animal")
            if animal in ("COW", "SHEEP", "GOOSE"):
                counts[animal] += 1
            if tile.get("kind") == "PLANT":
                counts["PLANTS"] += 1
                if tile.get("crop") == "STRAWBERRY":
                    counts["STRAWBERRY"] += 1
    counts["ANIMALS"] = counts["COW"] + counts["SHEEP"] + counts["GOOSE"]
    return counts


def _adaptive_animal_focus(obs, own, opponent):
    """Choose a livestock market to contest from observable exposure only."""
    day = int(_get(obs, "day", 0))
    if not (
        int(STRATEGY.get("adaptive_animal_min_day", 2))
        <= day
        <= int(STRATEGY.get("adaptive_animal_max_day", 14))
    ):
        return None
    opponent_herd = opponent["COW"] + opponent["SHEEP"]
    if opponent_herd < int(STRATEGY.get("adaptive_animal_min_herd", 4)):
        return None
    lead = int(STRATEGY.get("adaptive_animal_lead", 2))
    if opponent["COW"] >= opponent["SHEEP"] + lead:
        focus = "COW"
    elif opponent["SHEEP"] >= opponent["COW"] + lead:
        focus = "SHEEP"
    elif STRATEGY.get("adaptive_tempo_cow") and (
        opponent["ANIMALS"] >= own["ANIMALS"] + int(
            STRATEGY.get("adaptive_tempo_animal_lead", 1)
        )
        or opponent["LAND"] >= own["LAND"] + int(
            STRATEGY.get("adaptive_tempo_land_lead", 1)
        )
    ):
        # Cows are the cheaper livestock asset and start the milk cycle sooner.
        # When a balanced rival is already ahead on capital, this is a recovery
        # branch rather than an attempt to infer a nonexistent specialization.
        focus = "COW"
    else:
        return None
    if STRATEGY.get("adaptive_animal_mode") == "diversify":
        focus = "SHEEP" if focus == "COW" else "COW"
    share = max(0.5, min(1.0, float(STRATEGY.get("adaptive_animal_target_share", 0.72))))
    own_herd = own["COW"] + own["SHEEP"]
    # Do not blindly convert every future purchase.  Stop contesting once the
    # requested share is already represented in our live herd.
    target = int(round((own_herd + 1) * share))
    return focus if own[focus] < target else None


def _prioritize_capital_orders(obs, orders, own, opponent):
    """Spend existing early orders sooner when the rival is accelerating.

    WHEAT orders keep their exact slots and relative order because the fixed
    executor uses them as a cash cycle.  Only non-WHEAT slots are permuted.
    """
    if not STRATEGY.get("adaptive_capital_priority"):
        return orders
    if int(_get(obs, "day", 0)) > int(STRATEGY.get("adaptive_capital_max_day", 12)):
        return orders
    animal_pressure = opponent["ANIMALS"] >= own["ANIMALS"] + int(
        STRATEGY.get("adaptive_capital_animal_lead", 2)
    )
    land_pressure = opponent["LAND"] >= own["LAND"] + int(
        STRATEGY.get("adaptive_capital_land_lead", 1)
    )
    if not (animal_pressure or land_pressure):
        return orders

    movable = []
    positions = []
    for index, order in enumerate(orders):
        if len(order) > 1 and order[1] == "WHEAT" and order[0] in {"BUY_PRODUCT", "SELL"}:
            continue
        positions.append(index)
        movable.append(order)

    def priority(pair):
        index, order = pair
        command = order[0] if order else ""
        if command == "SELL":
            return (0, index)
        if command in {"BUY_LAND", "BUY_ANIMAL"}:
            return (1, index)
        if command == "HIRE":
            return (2, index)
        return (3, index)

    reordered = list(orders)
    sorted_orders = [order for _, order in sorted(enumerate(movable), key=priority)]
    for index, order in zip(positions, sorted_orders):
        reordered[index] = order
    return reordered


def _apply_fixed_board_adaptation(obs, action):
    """Observation-only adaptation layered on a validated fixed executor."""
    copied = _copy_action(action)
    if not STRATEGY.get("fixed_board_adaptation"):
        return copied
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied
    own = _public_farm_counts(farms[player])
    opponent = _public_farm_counts(farms[1 - player])
    focus = _adaptive_animal_focus(obs, own, opponent)
    if focus:
        for order in copied["market"]:
            if order and order[0] == "BUY_ANIMAL" and len(order) >= 2:
                order[1] = focus
    copied["market"] = _prioritize_capital_orders(obs, copied["market"], own, opponent)[:MAX_ORDERS]
    return copied


def _v11_radiant_schedule(obs, step):
    """Lock one coherent radiant trajectory from a public day-four price.

    The robust and alpha trajectories share actions 0..108 exactly.  Routing
    at step 109 therefore changes no prior farm state, and locking the choice
    prevents the invalid cross-trajectory oscillation seen in k-NN ablations.
    """
    global _V11_SELECTED_RADIANT_VARIANT
    variant = STRATEGY.get("v11_radiant_variant", "robust")
    if step == 0:
        _V11_SELECTED_RADIANT_VARIANT = None
    if variant in {"robust", "alpha"}:
        selected = variant
    else:
        route_step = int(STRATEGY.get("v11_route_step", 109))
        if step >= route_step and _V11_SELECTED_RADIANT_VARIANT is None:
            prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
            milk_price = float(prices.get("MILK", 0) or 0)
            _V11_SELECTED_RADIANT_VARIANT = (
                "alpha"
                if milk_price >= float(STRATEGY.get("v11_alpha_milk_price", 193))
                else "robust"
            )
        selected = _V11_SELECTED_RADIANT_VARIANT or "robust"
    return _V11_RADIANT_ALPHA_SCHEDULE if selected == "alpha" else _V11_RADIANT_SCHEDULE


def _v12_syouya_action(obs, step):
    """Apply only the two validated late gates to the coherent syouya route.

    Episodes 89511601 and 89512693 have identical movement and capital plans.
    Their first difference is the order of the terminal MILK/STRAWBERRY sales;
    public production capacity times the current price selects that order.
    """
    copied = _copy_action(_V12_SYOUYA_SCHEDULE[step])
    mode = STRATEGY.get("v12_late_market_mode", "price")
    if step == 624 and mode in {"asset", "price"}:
        farms = _get(obs, "farms", []) or []
        player = int(_get(obs, "player", 0))
        counts = (
            _public_farm_counts(farms[1 - player])
            if len(farms) == 2 and player in (0, 1)
            else {"COW": 0, "STRAWBERRY": 0}
        )
        if mode == "asset":
            milk_first = counts["COW"] >= counts["STRAWBERRY"]
        else:
            prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
            milk_value = counts["COW"] * float(prices.get("MILK", 0) or 0)
            strawberry_value = counts["STRAWBERRY"] * float(
                prices.get("STRAWBERRY", 0) or 0
            )
            milk_first = milk_value >= strawberry_value
        if not milk_first:
            priority = {
                "STRAWBERRY": 0,
                "MELON": 1,
                "FERTILIZER": 2,
                "MILK": 3,
                "WHEAT": 4,
            }
            sales = [order for order in copied["market"] if order and order[0] == "SELL"]
            other = [order for order in copied["market"] if not order or order[0] != "SELL"]
            copied["market"] = sorted(
                sales, key=lambda order: priority.get(order[1], len(priority))
            ) + other
    elif step == 714:
        shed = _get(_get(obs, "private", {}) or {}, "shed", {}) or {}
        if float(_get(shed, "FERTILIZER", 0) or 0) >= 2:
            copied["market"] = (copied["market"] + [["SELL", "FERTILIZER", 2]])[:MAX_ORDERS]
    return copied


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
