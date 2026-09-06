import re

with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update CROPS["WHEAT"] last_plant from 24 to 27 (matures in 2 days!)
old_crops_wheat = '"WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 24}'
new_crops_wheat = '"WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 27}'
assert old_crops_wheat in code, "old_crops_wheat not found"
code = code.replace(old_crops_wheat, new_crops_wheat)

# 2. Priority and EV boost for COLLECT_FERTILIZER: priority 2, EV p_fert * 1.5
old_fert_task = 'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))'
new_fert_task = 'tasks.append(_task(2, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.5))'
assert old_fert_task in code, "old_fert_task not found"
code = code.replace(old_fert_task, new_fert_task)

# 3. Fertilizer reserve and selling: keep at most 2 in reserve before Day 25, 0 after Day 25
old_fert_reserve = """    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""

new_fert_reserve = """    # Active Fertilizer Monetization: keep small buffer (2) for active application, monetize all excess!
    fert_reserve = min(fertilizer, 2) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""
assert old_fert_reserve in code, "old_fert_reserve not found"
code = code.replace(old_fert_reserve, new_fert_reserve)

# 4. Wheat feed buffer: animal_count + 1 before Day 28, 0 on Day 28+ (100% liquidation)
old_wheat_buffer = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)
    wheat_surplus = max(0, wheat_shed - wheat_feed_buffer)
    if wheat_surplus > 0 and len(orders) < MAX_ORDERS:
        orders.append(["SELL", "WHEAT", wheat_surplus])
        unit_w = float(prices.get("WHEAT", 1)) * 0.95
        budget += wheat_surplus * unit_w
        _MATCH_LEDGER["wheat_sold"] += wheat_surplus"""

new_wheat_buffer = """    # Feed Buffer Right-Sizing: 1 day buffer (animal_count + 1) during season, 100% liquidation on Day 28+!
    wheat_feed_buffer = 0 if day >= 28 else (animal_count + 1)
    wheat_surplus = max(0, wheat_shed - wheat_feed_buffer)
    if wheat_surplus > 0 and len(orders) < MAX_ORDERS:
        orders.append(["SELL", "WHEAT", wheat_surplus])
        unit_w = float(prices.get("WHEAT", 1)) * 0.95
        budget += wheat_surplus * unit_w
        _MATCH_LEDGER["wheat_sold"] += wheat_surplus"""
assert old_wheat_buffer in code, "old_wheat_buffer not found"
code = code.replace(old_wheat_buffer, new_wheat_buffer)

with open(r"D:\kaggriculture\scratch\candidate_rc15_v1.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created scratch/candidate_rc15_v1.py successfully!")
