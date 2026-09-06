with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Controlled Fertilizer Reserve: Cap at 14 for 100% strawberry protection, monetize all surplus
old_fert_reserve = """    # If strawberry price < 60, fertilizing strawberries has lower ROI than selling fertilizer at $40-$50!
    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""

new_fert_reserve = """    # Active Fertilizer Monetization: reserve up to 14 for 100% strawberry protection, monetize all surplus!
    fert_reserve = min(fertilizer, min(14, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""
assert old_fert_reserve in code, "old_fert_reserve not found"
code = code.replace(old_fert_reserve, new_fert_reserve)

# 2. Wheat feed buffer: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29
old_wheat_buf = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)"""
new_wheat_buf = """    # Day 28-29 Wheat Liquidation: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29!
    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""
assert old_wheat_buf in code, "old_wheat_buf not found"
code = code.replace(old_wheat_buf, new_wheat_buf)

# 3. Affluent Cow Expansion Gate on Day 11 with Feed Capacity Protection
old_animal_gate = """    for animal in ("COW", "SHEEP"):
        # Day-10 Amortization Horizon: Never buy animals after Day 10 (cows take 8+ days to yield!)
        if day > 10: break"""

new_animal_gate = """    # Dynamic Herd Carrying Capacity check:
    tiles = farm.get("tiles", [])
    wheat_plots = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
    current_herd = counts["COW"] + counts["SHEEP"]
    max_carrying_capacity = max(4, int(wheat_plots * 1.5))

    for animal in ("COW", "SHEEP"):
        # Amortization Horizon: Hard cutoff after Day 11
        if day > 11: break
        # On Day 11: Affluent Cow Gate (budget >= 8000, Cows only, herd <= capacity)
        if day == 11:
            if animal != "COW" or budget < 8000 or current_herd >= max_carrying_capacity:
                continue"""
assert old_animal_gate in code, "old_animal_gate not found"
code = code.replace(old_animal_gate, new_animal_gate)

with open(r"D:\kaggriculture\scratch\candidate_rc15_final.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created candidate_rc15_final.py cleanly!")
