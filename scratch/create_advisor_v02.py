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
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95

    # === SURGICAL ADVISOR v0.2: CRASH PREEMPTION & WORKING CAPITAL PROTECTION ===
    inv = _get(market, "inventory", {}) or {}
    prev_inv = getattr(_market_orders, "_prev_inv", {})
    di_milk = int(inv.get("MILK", 10000)) - int(prev_inv.get("MILK", 10000))
    _market_orders._prev_inv = dict(inv)

    p_milk = float(prices.get("MILK", 0) or 0)
    milk_in_shed = int(shed.get("MILK", 0))
    promote_milk = (p_milk >= 180.0 and di_milk > 0 and milk_in_shed > 0)

    sell_sequence = list(SELLABLE)
    if promote_milk:
        if budget >= 600 and fert_sale > 0:
            # Comfortable cash: Milk takes Slot 0, Fertilizer takes Slot 1
            orders.pop() # remove fertilizer from slot 0
            orders.append(["SELL", "MILK", milk_in_shed])
            budget += milk_in_shed * p_milk * 0.95
            _MATCH_LEDGER["milk_revenue"] += milk_in_shed * p_milk * 0.95
            orders.append(["SELL", "FERTILIZER", fert_sale])
            sell_sequence.remove("MILK")
        else:
            # Tight cash (<600) or no fert: Fertilizer stays Slot 0, Milk takes Slot 1
            sell_sequence.remove("MILK")
            sell_sequence.insert(0, "MILK")

    for item in sell_sequence:
        quantity = int(shed.get(item, 0))
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            unit_val = float(prices.get(item, 1)) * 0.95
            budget += quantity * unit_val
            if item == "MILK": _MATCH_LEDGER["milk_revenue"] += quantity * unit_val
            elif item == "WOOL": _MATCH_LEDGER["wool_revenue"] += quantity * unit_val
            elif item == "WHEAT": _MATCH_LEDGER["wheat_sold"] += quantity"""

assert target in code, "Target block not found in submission_rc2_terminal_horizon.py!"
new_code = code.replace(target, replacement, 1)

with open("submission_rc2_market_advisor_v02.py", "w") as f:
    f.write(new_code)

print("Successfully created submission_rc2_market_advisor_v02.py!")
