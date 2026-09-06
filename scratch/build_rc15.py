with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add FERTILIZER to SELLABLE so free manure is always monetized!
target_sellable = 'SELLABLE = ("MILK", "WOOL", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "EGG")'
repl_sellable = 'SELLABLE = ("MILK", "WOOL", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "EGG", "FERTILIZER")'
assert target_sellable in code, "Target sellable not found"
code = code.replace(target_sellable, repl_sellable)

# Add Day 28 Wheat Liquidation: Sell 100% of remaining wheat on Day 28+ (game ends on Day 29!)
target_liquidation = """    # Liquidate everything on day 28
    if day >= 28:
        for item in SELLABLE:
            qty = int(shed.get(item, 0))
            if qty > 0 and len(orders) < 10:
                orders.append(["SELL", item, qty])"""

repl_liquidation = """    # Liquidate everything on day 28 (including all accumulated feed wheat!)
    if day >= 28:
        for item in list(SELLABLE) + ["WHEAT"]:
            qty = int(shed.get(item, 0))
            if qty > 0 and len(orders) < 10:
                orders.append(["SELL", item, qty])"""
assert target_liquidation in code, "Target liquidation not found"
code = code.replace(target_liquidation, repl_liquidation)

# Priority boost for COLLECT_FERTILIZER: elevate priority from 4 to 2 so free manure is actually collected!
target_fert_task = 'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))'
repl_fert_task = 'tasks.append(_task(2, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.5))'
assert target_fert_task in code, "Target fert task not found"
code = code.replace(target_fert_task, repl_fert_task)

with open(r"D:\kaggriculture\submission_rc15.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc15.py successfully!")
