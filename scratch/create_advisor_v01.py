with open("submission_rc2_terminal_horizon.py", "r") as f:
    code = f.read()

target = """    # If strawberry price < 60, fertilizing strawberries has lower ROI than selling fertilizer at $40-$50!
    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95

    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""

replacement = """    # If strawberry price < 60, fertilizing strawberries has lower ROI than selling fertilizer at $40-$50!
    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    sell_orders = []
    if fert_sale > 0:
        sell_orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95

    for item in SELLABLE:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            sell_orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity

    # === MARKET ADVISOR v0.1: CRASH RISK & LIQUIDITY-AWARE QUEUE REORDERING ===
    inv = _get(market, "inventory", {}) or {}
    milk_crash_risk = (float(prices.get("MILK", 0) or 0) >= 180.0 and int(inv.get("MILK", 10000)) >= 10000)
    straw_crash_risk = (float(prices.get("STRAWBERRY", 0) or 0) >= 120.0 and int(inv.get("STRAWBERRY", 10000)) >= 10000)

    if milk_crash_risk or straw_crash_risk:
        def _advisor_priority(ord_item):
            item = ord_item[1]
            if item == "FERTILIZER" and budget < 600: return 0 # Urgent morning working capital
            if item == "MILK" and milk_crash_risk: return 1
            if item == "STRAWBERRY" and straw_crash_risk: return 2
            if item == "WOOL": return 3
            if item == "FERTILIZER": return 4
            return 10 # Others keep normal relative order
        sell_orders.sort(key=_advisor_priority)

    orders.extend(sell_orders)"""

assert target in code, "Target block not found in submission_rc2_terminal_horizon.py!"
new_code = code.replace(target, replacement, 1)

with open("submission_rc2_market_advisor_v01.py", "w") as f:
    f.write(new_code)

print("Successfully created submission_rc2_market_advisor_v01.py!")
