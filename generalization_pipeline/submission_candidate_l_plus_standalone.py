"""Candidate L+ Standalone Kaggle Submission Artifact.

100% Self-Contained single-file Kaggle entrypoint.
Combines V4.1 Dynamic Core Engine + 10-Melon Opening + Opponent-Aware Milk Ranker + 8-Cow Ceiling.
"""

from __future__ import annotations

import base64
import json
import math
import zlib
import sys


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

ANIMAL_SITES = (
    (4, 2), (4, 3), (3, 4), (4, 4),
    (6, 2), (5, 3), (7, 3), (5, 4), (7, 4),
    (3, 5), (4, 5), (3, 6), (4, 6), (4, 7),
)

DEFAULT_STRATEGY = {
    "hands": 13,
    "cows": 8,
    "sheep": 6,
    "strawberries": 34,
    "strawberry_last_plant": 18,
    "fertilizer_roi": 1.5,
    "opening_wheat": 10,
    "opening_melons": 10,  # Candidate L+ 10-Melon Opening
    "opening_carrots": 2,
    "opening_animals": 2,
    "opening_cows": None,
    "opening_sheep": None,
    "crop_transition_day": 5,
    "strawberry_activation_day": 4,
    "strawberry_staging": False,
    "opening_melon_day0_cap": None,
    "opening_melon_early_cap": None,
    "top_hire_ramp": False,
    "land_ne_day": 5,
    "land_sw_day": 10,
    "animal_nw_day": 4,
    "animal_ne_day": 8,
    "animal_sw_day": 12,
    "feed_days_buffer": 1,
    "ongoing_harvest_threshold": 3,
    "drop_load_threshold": 30,
    "price_adaptive_animals": False,
    "animal_price_sensitivity": 2.0,
    "zoned_workers": False,
    "use_fixed_schedule": False,  # Candidate L+ Pure Dynamic Core
    "fixed_schedule_version": "v18",
}

STRATEGY = dict(DEFAULT_STRATEGY)


def configure_strategy(overrides=None):
    global STRATEGY
    STRATEGY = dict(DEFAULT_STRATEGY)
    if overrides:
        STRATEGY.update(overrides)


def _get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


# Import core v18 helper functions from kaitofukami-v18
import importlib.util
V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
spec = importlib.util.spec_from_file_location("v18_base_standalone", V18_PATH)
mod_v18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod_v18)

mod_v18.configure_strategy({
    "use_fixed_schedule": False,
    "v13_market_adaptation": True,
    "opening_melons": 10,
    "cows": 8,
})

_base_v18_agent = mod_v18.agent


def agent(obs, configuration=None):
    """Candidate L+ Kaggle Entrypoint."""
    action_dict = _base_v18_agent(obs)
    market_orders = action_dict.get("market", [])
    if not market_orders or len(market_orders) <= 1:
        return action_dict

    prices = mod_v18._get(mod_v18._get(obs, "market", {}), "prices", {}) or {}
    milk_p_data = prices.get("MILK", 0.0)
    milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

    # Opponent-Aware Milk Ranker
    def order_priority(idx_order):
        idx, ord_item = idx_order
        if not ord_item or ord_item[0] != "SELL":
            return (10, idx)
        item = ord_item[1] if len(ord_item) > 1 else ""
        if item == "MILK" and milk_p >= 230.0:
            return (0, idx)
        elif item == "MELON":
            return (1, idx)
        elif item == "STRAWBERRY":
            return (2, idx)
        elif item == "WHEAT":
            return (3, idx)
        return (4, idx)

    reordered = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)]
    action_dict["market"] = reordered
    return action_dict
