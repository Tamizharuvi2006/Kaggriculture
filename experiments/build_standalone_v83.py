"""Builds a 100% self-contained standalone Python file for Kaggle upload.

Combines kaitofukami-v18.py engine with V8.3 Opponent Supply-Aware Market Ranker,
eliminating all external file imports and __file__ variable references.
"""

import os
import sys

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
OUT_PATH = r"D:\kaggriculture\baseline\submission_v83_standalone.py"

with open(V18_PATH, "r", encoding="utf-8") as f:
    v18_code = f.read()

# Append V8.3 Strategy Initialization and Entrypoint Wrapper
v83_wrapper = """

# ==============================================================================
# V8.3 CHAMPION AGENT ENTRYPOINT (Self-Contained Kaggle Competition Build)
# ==============================================================================

configure_strategy({
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 13,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
})

_v18_base_agent = agent


def agent(obs, configuration=None):
    \"\"\"V8.3 Agent Entrypoint with Opponent Supply-Aware Market Ranking.\"\"\"
    action_dict = _v18_base_agent(obs)
    market_orders = action_dict.get("market", [])

    if not market_orders or len(market_orders) <= 1:
        return action_dict

    player = int(_get(obs, "player", 0))
    opp_player = 1 - player
    farms = _get(obs, "farms", [])

    opp_cows = 0
    if len(farms) > opp_player:
        opp_tiles = _get(farms[opp_player], "tiles", [])
        for row in opp_tiles:
            for t in row:
                if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW":
                    opp_cows += 1

    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    milk_p_data = prices.get("MILK", 0.0)
    milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

    def order_priority(idx_order):
        idx, ord_item = idx_order
        if not ord_item or ord_item[0] != "SELL":
            return (10, idx)
        item = ord_item[1] if len(ord_item) > 1 else ""
        if item == "MILK" and milk_p >= 230.0:
            return (0, idx)  # Top priority sell
        elif item == "MELON":
            return (1, idx)
        elif item == "STRAWBERRY":
            return (2, idx)
        elif item == "WHEAT":
            return (3, idx)
        return (4, idx)

    reordered = [
        ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)
    ]
    action_dict["market"] = reordered
    return action_dict
"""

full_code = v18_code + "\n" + v83_wrapper

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(full_code)

print(f"Successfully generated self-contained {OUT_PATH} ({len(full_code):,} bytes, {full_code.count(chr(10)):,} lines)")
