with open(r"D:\kaggriculture\submission_rc6_d.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Animal herd composition: 8 cows + 2 sheep
target_plan = """def _animal_plan():
    return _build_animal_plan(8, 4)"""
repl_plan = """def _animal_plan():
    return _build_animal_plan(8, 2)"""
assert target_plan in code, "Target plan not found"
code = code.replace(target_plan, repl_plan)

# 2. Animal purchase cutoff: Day 10 cutoff
target_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""

repl_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        # Strict Amortization Rule: Never buy animals after Day 10 (need 18+ days to pay back!)
        if day > 10: break
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""
assert target_animal_loop in code, "Target animal loop not found"
code = code.replace(target_animal_loop, repl_animal_loop)

# 3. Capitalized land expansion: Day 8 for NE ($1,000 reserve), Day 10 for SW ($1,000 reserve)
target_land = """    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 9 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    land_cost = 0
    land_reserve = 1000
    if len(unlocked) == 1 and day >= 8 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""
assert target_land in code, "Target land not found"
code = code.replace(target_land, repl_land)

# 4. Market pricing protection against dumping below $30 before Day 28
target_sell = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""

repl_sell = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            p = float(prices.get(item, 1))
            # Protect against catastrophic $1 dumps before Day 28 liquidation
            if day < 28 and p < 30.0:
                continue
            orders.append(["SELL", item, quantity])
            unit_val = p * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""
assert target_sell in code, "Target sell not found"
code = code.replace(target_sell, repl_sell)

# 5. Labor ramp tuned to active quadrants
target_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 1: return 4
    if day <= 4: return 5
    if day <= 7: return 7
    if day <= 11: return 9
    if day <= 28: return 12
    return 6"""

repl_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 2: return 3
    if day <= 5: return 5
    if day <= 7: return 7
    if day <= 10: return 9
    if day <= 28: return 12
    return 6"""
assert target_labor in code, "Target labor not found"
code = code.replace(target_labor, repl_labor)

target_crit = """    critical_target = min(target_hires, 4 if day <= 1 else 5 if day <= 4 else 7 if day <= 7 else 9 if day <= 11 else 12)"""
repl_crit = """    critical_target = min(target_hires, 3 if day <= 2 else 5 if day <= 5 else 7 if day <= 7 else 9 if day <= 10 else 12)"""
assert target_crit in code, "Target critical labor not found"
code = code.replace(target_crit, repl_crit)

with open(r"D:\kaggriculture\submission_rc8.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc8.py successfully!")
