"""Clean Candidate L+ Builder Script.

Reads baseline/kaitofukami-v18.py (V4.1 Master 1714.4 Champion) and produces a 100% self-contained, clean submission file:
generalization_pipeline/submission_candidate_l_plus.py

Features:
1. Preserves complete V4.1 Core Engine, v18 fixed opening/expansion schedule, state repair, animal management, harvesting, and dynamic market logic.
2. Configures opening_melons = 10.
3. Applies Opponent-Aware Milk Ranker re-ordering SELL orders when MILK >= $230.0.
"""

import os

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
OUT_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"

with open(V18_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Modify opening_melons to 10
content = content.replace('"opening_melons": 9,', '"opening_melons": 10,')

# 2. Add Opponent-Aware Milk Ranker into _v18_closed_loop_action
old_closed_loop_return = """    return {
        "farmer": list(board_action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (board_action.get("hands") or [])],
        "market": [list(order) for order in (market_action.get("market") or [])],
    }"""

new_closed_loop_return = """    market_orders = [list(order) for order in (market_action.get("market") or [])]
    if market_orders and len(market_orders) > 1:
        prices = _get(_get(obs, "market", {}), "prices", {}) or {}
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)
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
        market_orders = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)]

    return {
        "farmer": list(board_action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (board_action.get("hands") or [])],
        "market": market_orders,
    }"""

assert old_closed_loop_return in content, "Error: target snippet not found in kaitofukami-v18.py!"

content = content.replace(old_closed_loop_return, new_closed_loop_return)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully generated clean Candidate L+ artifact at {OUT_PATH} (Size: {os.path.getsize(OUT_PATH)} bytes)")
