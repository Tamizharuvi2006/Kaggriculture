with open(r"D:\kaggriculture\submission_rc6_d.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Strategy configuration: 3 Cows, 1 Sheep, 7 Melons, 10 Wheat, 2 Carrots, up to 14 total animals
target_strat = """    'opening_animals': 2,
    'opening_carrots': 2,
    'opening_cows': 2,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 9,
    'opening_sheep': 0,
    'opening_wheat': 10,"""

repl_strat = """    'opening_animals': 4,
    'opening_carrots': 2,
    'opening_cows': 3,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 7,
    'opening_sheep': 1,
    'opening_wheat': 10,"""
assert target_strat in code, "Target strat not found"
code = code.replace(target_strat, repl_strat)

# 2. Herd target: 8 cows + 6 sheep = 14 animals
target_animal_plan = """def _animal_plan():
    return _build_animal_plan(8, 4)"""
repl_animal_plan = """def _animal_plan():
    return _build_animal_plan(8, 6)"""
assert target_animal_plan in code, "Target animal plan not found"
code = code.replace(target_animal_plan, repl_animal_plan)

# 3. Labor ramp: scaling up to 13 workers
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
    if day <= 1: return 4
    if day <= 3: return 5
    if day <= 5: return 6
    if day <= 7: return 8
    if day <= 10: return 10
    if day <= 28: return 13
    return 6"""
assert target_labor in code, "Target labor not found"
code = code.replace(target_labor, repl_labor)

# Critical target labor
target_crit = """    critical_target = min(target_hires, 4 if day <= 1 else 5 if day <= 4 else 7 if day <= 7 else 9 if day <= 11 else 12)"""
repl_crit = """    critical_target = min(target_hires, 4 if day <= 1 else 5 if day <= 3 else 6 if day <= 5 else 8 if day <= 7 else 10 if day <= 10 else 13)"""
assert target_crit in code, "Target critical labor not found"
code = code.replace(target_crit, repl_crit)

# 4. Animal purchase cap: up to 6 per day
target_cap = """def _animal_purchase_cap():
    return 4"""
repl_cap = """def _animal_purchase_cap():
    return 6"""
assert target_cap in code, "Target cap not found"
code = code.replace(target_cap, repl_cap)

# 5. Market reservation price floor and fertilizer/wheat sales
target_sales = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""

repl_sales = """    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            unit_p = float(prices.get(item, 1))
            # Protect against selling into temporary market crashes before Day 28 liquidation
            if day < 28:
                if item == "STRAWBERRY" and unit_p < 70.0: continue
                if item in ("MILK", "WOOL") and unit_p < 60.0: continue
                if item == "MELON" and unit_p < 100.0: continue
            orders.append(["SELL", item, quantity])
            unit_val = unit_p * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""
assert target_sales in code, "Target sales not found"
code = code.replace(target_sales, repl_sales)

# 6. Feed grain buffer in market maintenance: buy up to 2-3 days of feed
target_feed = """    # Emergency Feed Protection: NEVER allow an existing animal to starve!
    # Sunk capital is $400-$500 per animal. A missed feed destroys the entire animal.
    wheat_total = wheat_shed + sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    if wheat_total < animal_count and day < 28:
        feed_needed = animal_count - wheat_total
        p_wheat_buy = _safe_buy_price(prices.get("WHEAT", 25))
        buy_q = min(feed_needed, int(budget // p_wheat_buy))
        if buy_q > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_PRODUCT", "WHEAT", buy_q])"""

repl_feed = """    # Dynamic Feed Protection: maintain 2-day on-farm grain buffer
    wheat_total = wheat_shed + sum(int(inv.get("WHEAT", 0)) for inv in inventories if isinstance(inv, dict))
    target_grain_buffer = min(20, animal_count * 2) if day < 27 else animal_count
    if wheat_total < target_grain_buffer and day < 28:
        feed_needed = target_grain_buffer - wheat_total
        p_wheat_buy = _safe_buy_price(prices.get("WHEAT", 25))
        buy_q = min(feed_needed, int(budget // p_wheat_buy))
        if buy_q > 0 and len(orders) < MAX_ORDERS:
            orders.append(["BUY_PRODUCT", "WHEAT", buy_q])"""
assert target_feed in code, "Target feed not found"
code = code.replace(target_feed, repl_feed)

with open(r"D:\kaggriculture\submission_rc7.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc7.py successfully!")
