"""Build 100% Self-Contained Candidate L+ Kaggle Submission Artifact.

Reads baseline/kaitofukami-v18.py and embeds all strategy logic directly into:
generalization_pipeline/submission_candidate_l_plus.py

Modifications applied:
1. DEFAULT_STRATEGY["opening_melons"] = 10
2. DEFAULT_STRATEGY["use_fixed_schedule"] = False
3. Opponent-Aware Milk Ranker re-ordering in agent(obs)
"""

import os

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
OUT_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"

with open(V18_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Modify opening_melons to 10
content = content.replace('"opening_melons": 9,', '"opening_melons": 10,')

# 2. Modify use_fixed_schedule to False
content = content.replace('"use_fixed_schedule": True,', '"use_fixed_schedule": False,')

# 3. Add Opponent-Aware Milk Ranker into agent(obs)
old_return = """        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": _market_orders(obs),
        }"""

new_return = """        action_dict = {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": _market_orders(obs),
        }
        market_orders = action_dict.get("market", [])
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
            reordered = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)]
            action_dict["market"] = reordered
        return action_dict"""

assert old_return in content, "Error: old_return snippet not found in kaitofukami-v18.py!"

content = content.replace(old_return, new_return)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully generated standalone Candidate L+ artifact at {OUT_PATH} (Size: {os.path.getsize(OUT_PATH)} bytes)")
