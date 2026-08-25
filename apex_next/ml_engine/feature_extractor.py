"""Real observation feature extraction for the APEX 4.1 hybrid ML plan.

The old quarantined ML branch used synthetic random vectors. This module only
derives features from the actual Kaggriculture observation dictionary.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np


FEATURE_DIM = 128
OPPONENT_SLICE = slice(60, 84)

PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "MILK",
    "WOOL",
    "EGG",
    "FERTILIZER",
    "WHEAT_SEEDS",
    "CARROT_SEEDS",
    "STRAWBERRY_SEEDS",
)

PRICE_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "MILK",
    "WOOL",
    "FERTILIZER",
)

DEFAULT_PRICES = {
    "WHEAT": 10.0,
    "CARROT": 20.0,
    "TOMATO": 50.0,
    "STRAWBERRY": 120.0,
    "MELON": 80.0,
    "MILK": 193.0,
    "WOOL": 150.0,
    "FERTILIZER": 100.0,
}

CROP_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")


def extract_features(obs: dict[str, Any]) -> np.ndarray:
    """Convert a real Kaggriculture observation into 128 float32 features."""

    features = np.zeros(FEATURE_DIM, dtype=np.float32)
    if not isinstance(obs, dict):
        return features

    step = _as_int(_get(obs, "step", 0))
    farms = _as_list(_get(obs, "farms", []))
    player = _player_index(obs, len(farms))
    our_farm = farms[player] if player < len(farms) else {}
    opp_index = 1 - player if len(farms) == 2 else 1
    opp_farm = farms[opp_index] if opp_index < len(farms) else {}
    private = _as_mapping(_get(obs, "private", {}))
    shed = _as_mapping(_get(private, "shed", {}))
    market = _as_mapping(_get(obs, "market", {}))
    prices = _prices(market)

    _fill_time_features(features, step)
    own_stats = _farm_stats(our_farm)
    opp_stats = _farm_stats(opp_farm)
    _fill_own_economy(features, own_stats)
    _fill_inventory(features, shed)
    _fill_market(features, prices)
    _fill_own_tiles(features, own_stats)
    _fill_opponent(features, own_stats, opp_stats)
    _fill_derived(features, step, own_stats, opp_stats, shed, prices)

    np.nan_to_num(features, copy=False, nan=0.0, posinf=1e6, neginf=-1e6)
    return features.astype(np.float32, copy=False)


def opponent_features(features: np.ndarray) -> np.ndarray:
    """Return the 24-dimensional opponent-classifier input slice."""

    return np.asarray(features, dtype=np.float32)[OPPONENT_SLICE]


def _fill_time_features(features: np.ndarray, step: int) -> None:
    safe_step = max(0, min(step, 720))
    features[0] = safe_step / 720.0
    features[1] = (safe_step // 24) / 30.0
    features[2] = (safe_step % 24) / 24.0
    features[3] = 1.0 - (safe_step / 720.0)


def _fill_own_economy(features: np.ndarray, stats: dict[str, Any]) -> None:
    money = stats["money"]
    animals = stats["animals"]
    features[4] = money / 10000.0
    features[5] = min(money / 2000.0, 1.0)
    features[6] = stats["quadrants"] / 4.0
    features[7] = animals["COW"] / 14.0
    features[8] = animals["SHEEP"] / 14.0
    features[9] = stats["animal_total"] / 14.0
    features[10] = stats["worker_count"] / 13.0
    features[11] = stats["idle_workers"] / max(stats["worker_count"], 1)
    features[12] = float(stats["quadrants"] >= 3)
    features[13] = min(money / 500.0, 1.0)


def _fill_inventory(features: np.ndarray, shed: dict[str, Any]) -> None:
    for index, product in enumerate(PRODUCTS):
        features[16 + index] = min(max(_as_float(_get(shed, product, 0.0)), 0.0) / 20.0, 1.0)


def _fill_market(features: np.ndarray, prices: dict[str, float]) -> None:
    for index, product in enumerate(PRICE_PRODUCTS):
        default_price = DEFAULT_PRICES[product]
        price = prices.get(product, default_price)
        features[28 + index] = price / (default_price * 2.0)
        features[36 + index] = (price - default_price) / default_price


def _fill_own_tiles(features: np.ndarray, stats: dict[str, Any]) -> None:
    tile_count = max(stats["tile_count"], 1)
    crop_counts = stats["crop_counts"]
    features[44] = stats["tilled_tiles"] / tile_count
    features[45] = stats["planted_tiles"] / tile_count
    features[46] = stats["watered_tiles"] / tile_count
    features[47] = stats["mature_tiles"] / tile_count
    features[48] = crop_counts["STRAWBERRY"] / 34.0
    features[49] = crop_counts["MELON"] / 12.0
    features[50] = crop_counts["WHEAT"] / 10.0
    features[51] = crop_counts["TOMATO"] / 8.0
    features[52] = crop_counts["CARROT"] / 8.0
    features[56] = float(stats["quadrants"] >= 1)
    features[57] = float(stats["quadrants"] >= 2)
    features[58] = float(stats["quadrants"] >= 3)


def _fill_opponent(features: np.ndarray, own: dict[str, Any], opp: dict[str, Any]) -> None:
    opp_animals = opp["animals"]
    opp_tile_count = max(opp["tile_count"], 1)
    opp_crops = opp["crop_counts"]
    features[60] = opp["money"] / 10000.0
    features[61] = opp["quadrants"] / 4.0
    features[62] = opp_animals["COW"] / 14.0
    features[63] = opp_animals["SHEEP"] / 14.0
    features[64] = opp["animal_total"] / 14.0
    features[65] = opp["worker_count"] / 13.0
    features[66] = opp["planted_tiles"] / opp_tile_count
    features[67] = opp["mature_tiles"] / opp_tile_count
    features[68] = opp_crops["STRAWBERRY"] / 34.0
    features[69] = opp_crops["MELON"] / 12.0
    features[70] = opp_crops["WHEAT"] / 10.0
    features[71] = opp_crops["TOMATO"] / 8.0
    features[72] = opp_crops["CARROT"] / 8.0
    features[73] = opp["money"] / max(own["money"], 1.0)
    features[74] = opp["animal_total"] / max(own["animal_total"], 1)
    features[75] = opp["worker_count"] / max(own["worker_count"], 1)
    features[76] = opp["quadrants"] / max(own["quadrants"], 1)
    features[80] = float(opp_animals["COW"] > opp_animals["SHEEP"] * 2)
    features[81] = float(opp_animals["SHEEP"] > opp_animals["COW"] * 2)
    features[82] = float(opp["planted_tiles"] > 20)
    features[83] = float(opp["quadrants"] > own["quadrants"])


def _fill_derived(
    features: np.ndarray,
    step: int,
    own: dict[str, Any],
    opp: dict[str, Any],
    shed: dict[str, Any],
    prices: dict[str, float],
) -> None:
    wealth = own["money"]
    for product in ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "CARROT"):
        wealth += _as_float(_get(shed, product, 0.0)) * prices.get(product, DEFAULT_PRICES.get(product, 0.0))

    features[84] = wealth / 100000.0
    features[85] = float(wealth > opp["money"] * 1.2)
    features[86] = float(step > 500)
    features[87] = float(step > 650)
    features[88] = float(own["animal_total"] >= 10)
    features[89] = float(own["money"] < 200 and step < 200)
    features[90] = (_as_float(_get(shed, "MILK", 0.0)) * prices.get("MILK", DEFAULT_PRICES["MILK"])) / 5000.0
    features[91] = (_as_float(_get(shed, "STRAWBERRY", 0.0)) * prices.get("STRAWBERRY", DEFAULT_PRICES["STRAWBERRY"])) / 5000.0
    features[92] = float(_as_float(_get(shed, "MILK", 0.0)) > 4)
    features[93] = float(_as_float(_get(shed, "STRAWBERRY", 0.0)) > 4)
    features[94] = max(0.0, (720 - step) / 720.0)
    features[95] = float(step >= 700)
    features[96] = float(step == 71)
    features[97] = float((step % 24) == 22)
    features[98] = float((step % 24) == 23)
    features[99] = float(prices.get("STRAWBERRY", DEFAULT_PRICES["STRAWBERRY"]) > 140)
    features[100] = float(prices.get("STRAWBERRY", DEFAULT_PRICES["STRAWBERRY"]) < 100)
    features[101] = float(prices.get("MILK", DEFAULT_PRICES["MILK"]) > 200)
    features[102] = float(prices.get("MILK", DEFAULT_PRICES["MILK"]) < 150)


def _farm_stats(farm: Any) -> dict[str, Any]:
    farm_map = _as_mapping(farm)
    unlocked = _as_list(_first_present(farm_map, ("unlocked_quadrants", "unlocked", "land"), ["NW"]))
    workers = _as_list(_get(farm_map, "workers", _get(farm_map, "hands", [])))
    animals = _animal_counts(farm_map)
    tiles = list(_iter_tiles(_get(farm_map, "tiles", [])))
    crop_counts = {crop: 0 for crop in CROP_PRODUCTS}
    tilled = planted = watered = mature = 0

    for tile in tiles:
        tile_map = _as_mapping(tile)
        crop = _normalize_item(_first_present(tile_map, ("crop", "planted", "plant", "item", "type"), ""))
        if _is_tilled(tile_map):
            tilled += 1
        if crop in crop_counts:
            crop_counts[crop] += 1
            planted += 1
        if _is_watered(tile_map):
            watered += 1
        if _is_mature(tile_map):
            mature += 1

    return {
        "money": _as_float(_first_present(farm_map, ("money", "cash"), 0.0)),
        "quadrants": max(len(unlocked), 1),
        "workers": workers,
        "worker_count": len(workers),
        "idle_workers": sum(1 for worker in workers if not _worker_carrying(worker)),
        "animals": animals,
        "animal_total": animals["COW"] + animals["SHEEP"],
        "tiles": tiles,
        "tile_count": len(tiles),
        "tilled_tiles": tilled,
        "planted_tiles": planted,
        "watered_tiles": watered,
        "mature_tiles": mature,
        "crop_counts": crop_counts,
    }


def _animal_counts(farm: dict[str, Any]) -> dict[str, int]:
    counts = {"COW": 0, "SHEEP": 0}
    animals = _get(farm, "animals", {})
    if isinstance(animals, dict):
        for name in counts:
            counts[name] += _as_int(_get(animals, name, 0))
    elif isinstance(animals, Iterable) and not isinstance(animals, (str, bytes)):
        for animal in animals:
            name = _normalize_item(_first_present(_as_mapping(animal), ("type", "name", "item"), animal))
            if name in counts:
                counts[name] += 1

    for tile in _iter_tiles(_get(farm, "tiles", [])):
        tile_map = _as_mapping(tile)
        name = _normalize_item(_first_present(tile_map, ("animal", "type", "item"), ""))
        if name in counts:
            counts[name] += 1
    return counts


def _prices(market: dict[str, Any]) -> dict[str, float]:
    raw_prices = _first_present(market, ("prices", "current_prices"), {})
    price_map = _as_mapping(raw_prices)
    prices = dict(DEFAULT_PRICES)
    for product in PRICE_PRODUCTS:
        prices[product] = _as_float(_get(price_map, product, prices[product]))
    return prices


def _iter_tiles(tiles: Any) -> Iterable[Any]:
    if isinstance(tiles, dict):
        yield from tiles.values()
    elif isinstance(tiles, Iterable) and not isinstance(tiles, (str, bytes)):
        for item in tiles:
            if isinstance(item, Iterable) and not isinstance(item, (dict, str, bytes)):
                yield from item
            else:
                yield item


def _player_index(obs: dict[str, Any], farm_count: int) -> int:
    player = _as_int(_first_present(obs, ("player", "index", "agentIndex"), 0))
    if 0 <= player < farm_count:
        return player
    return 0


def _worker_carrying(worker: Any) -> bool:
    worker_map = _as_mapping(worker)
    return bool(_first_present(worker_map, ("carrying", "item", "held_item", "holding"), None))


def _is_tilled(tile: dict[str, Any]) -> bool:
    if bool(_get(tile, "tilled", False)):
        return True
    state = str(_first_present(tile, ("state", "status"), "")).upper()
    return "TILLED" in state or bool(_first_present(tile, ("crop", "planted", "plant"), ""))


def _is_watered(tile: dict[str, Any]) -> bool:
    if bool(_get(tile, "watered", False)):
        return True
    state = str(_first_present(tile, ("state", "status"), "")).upper()
    return "WATER" in state


def _is_mature(tile: dict[str, Any]) -> bool:
    stage = str(_first_present(tile, ("stage", "growth", "status", "state"), "")).upper()
    return stage in {"RIPE", "MATURE", "READY", "HARVESTABLE"} or "RIPE" in stage


def _normalize_item(value: Any) -> str:
    text = str(value or "").upper()
    return text.replace(" ", "_").replace("-", "_")


def _first_present(mapping: Any, keys: tuple[str, ...], default: Any) -> Any:
    map_value = _as_mapping(mapping)
    for key in keys:
        value = _get(map_value, key, None)
        if value is not None:
            return value
    return default


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
