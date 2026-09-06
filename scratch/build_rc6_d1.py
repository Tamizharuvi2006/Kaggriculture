with open(r"D:\kaggriculture\submission_rc6_d.py", "r", encoding="utf-8") as f:
    code = f.read()

# Protect against fire-sale sales (< $25) before Day 28 liquidation
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
            # Protect against catastrophic fire-sale market dumps (< $25) before Day 28 liquidation
            if day < 28 and p < 25.0:
                continue
            orders.append(["SELL", item, quantity])
            unit_val = p * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""
assert target_sell in code, "Target sell not found"
code = code.replace(target_sell, repl_sell)

with open(r"D:\kaggriculture\submission_rc6_d1.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc6_d1.py successfully!")
