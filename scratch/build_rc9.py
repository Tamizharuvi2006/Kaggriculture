with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Livestock Herd Focus: 8 Cows, 2 Sheep
target_plan = """def _animal_plan():
    return _build_animal_plan(8, 4)"""
repl_plan = """def _animal_plan():
    return _build_animal_plan(8, 2)"""
assert target_plan in code, "Target plan not found"
code = code.replace(target_plan, repl_plan)

# 2. Hard Cutoff on Day 10 for Animal Purchases
target_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""

repl_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        # Strict Amortization Rule: Zero animal purchases after Day 10 (need 18+ days to pay back!)
        if day > 10: break
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""
assert target_animal_loop in code, "Target animal loop not found"
code = code.replace(target_animal_loop, repl_animal_loop)

# 3. Absorption-Matched Clearance: Rate-limit high-value product sales to town absorption rate (<= 6/turn)
target_sell = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            p = float(prices.get(item, 1))
            # Protect against catastrophic fire-sale market dumps (< $25) before Day 28 liquidation
            if day < 28 and p < 25.0:
                continue
            orders.append(["SELL", item, quantity])
            unit_val = p * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""

repl_sell = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            p = float(prices.get(item, 1))
            # Protect against catastrophic fire-sale market dumps (< $25) before Day 28 liquidation
            if day < 28 and p < 25.0:
                continue
            # Absorption-Matched Rate: Rate-limit sales to town absorption capacity (<= 6/turn) before Day 28
            sell_q = min(quantity, 6) if (day < 28 and item in ("MILK", "STRAWBERRY")) else quantity
            orders.append(["SELL", item, sell_q])
            unit_val = p * 0.95
            budget += sell_q * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += sell_q * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += sell_q * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += sell_q"""
assert target_sell in code, "Target sell not found"
code = code.replace(target_sell, repl_sell)

with open(r"D:\kaggriculture\submission_rc9.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc9.py successfully!")
