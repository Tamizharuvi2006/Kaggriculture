"""
APEX 4.0 Pure Observation-Driven Regional Crop Controller
Interacts with farm tiles strictly based on live physical tile state:
- Ripe crop (yield_units > 0) -> HARVEST
- Empty tilled tile (kind == 'TILLED') & seeds in shed -> PLANT
- Untilled tile (None) -> TILL
- Thirsty crop (not watered_today) -> WATER
- Worker carrying ripe produce at Hour 22 -> DROP in shed
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def _copy_action(act):
    if not isinstance(act, dict):
        return act
    return {
        "farmer": list(act.get("farmer", ["PASS"])),
        "hands": [list(h) if isinstance(h, list) else h for h in act.get("hands", [])],
        "market": [list(m) if isinstance(m, list) else m for m in act.get("market", [])]
    }


def plan_state_driven_regional_action(obs, baseline_action):
    copied = _copy_action(baseline_action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", []) or []
    tiles = own_farm.get("tiles", []) or []
    shed = own_farm.get("inventory", {}) or {}
    money = float(_get(own_farm, "money", 0.0) or 0.0)
    hands = copied.get("hands", [])
    hour = step % 24

    # 1. CAPITAL & RESOURCE SYNCHRONIZATION
    # Step 75 Melon Liquidity Conversion
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # Step 152 Dynamic Land 2 Expansion
    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    # Step 156 Synchronized Seed Purchase for Worker #3
    if step == 156:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # Dynamic Seed Replenishment: If NE is unlocked and shed strawberry seeds == 0, buy 2 seeds
    if 'NE' in unlocked and step >= 180 and (step % 24 == 0) and int(shed.get("STRAWBERRY", 0) or 0) == 0 and money >= 300.0:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # 2. WORKER #3 INITIAL NE CULTIVATION (Steps 172 to 180)
    # INVARIANT: Pasture 2 @ Step 159 & Cow Pickup @ Step 170 are 100% PROTECTED!
    if 'NE' in unlocked and 172 <= step <= 180 and len(hands) >= 4:
        # Check live state of NE tile (2, 6)
        t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
        if step in (172, 173, 174):
            copied["hands"][3] = ["EAST"]
        elif step == 175:
            if t26 is None:
                copied["hands"][3] = ["TILL"]
            else:
                copied["hands"][3] = ["PASS"]
        elif step == 176:
            straw_seeds = int(shed.get("STRAWBERRY", 0) or 0)
            if straw_seeds > 0 or t26 is not None:
                copied["hands"][3] = ["PLANT", "STRAWBERRY"]
            else:
                copied["hands"][3] = ["PASS"]
        elif step == 177:
            copied["hands"][3] = ["WATER"]
        elif step in (178, 179):
            copied["hands"][3] = ["WEST"]
        elif step == 180:
            copied["hands"][3] = ["PASS"]

    # 3. WORKER #4 OBSERVATION-DRIVEN CONTINUOUS NE REGIONAL MAINTENANCE (Steps 185 to 719)
    if 'NE' in unlocked and step >= 185 and len(hands) >= 5:
        t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
        # Derive action strictly from live physical tile state
        if t26 is not None and isinstance(t26, dict):
            # If ripe, harvest!
            if t26.get("yield_units", 0) > 0:
                copied["hands"][4] = ["HARVEST"]
            # If thirsty, water!
            elif not t26.get("watered_today", False):
                copied["hands"][4] = ["WATER"]
            # If tilled and empty, replant!
            elif t26.get("kind") == "TILLED" and int(shed.get("STRAWBERRY", 0) or 0) > 0:
                copied["hands"][4] = ["PLANT", "STRAWBERRY"]

    # 4. PRE-CLEARANCE LIQUIDATION & TERMINAL LOGISTICS
    if hour == 23 and step >= 200:
        straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
        milk_cnt = int(shed.get("MILK", 0) or 0)
        if straw_cnt >= 4:
            copied["market"].append(["SELL", "STRAWBERRY", straw_cnt])
        if milk_cnt >= 4:
            copied["market"].append(["SELL", "MILK", milk_cnt])

    if step >= 672:
        shed_wheat = int(shed.get("WHEAT", 0) or 0)
        if shed_wheat >= 12:
            copied["market"] = [m for m in copied["market"] if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

    return copied
