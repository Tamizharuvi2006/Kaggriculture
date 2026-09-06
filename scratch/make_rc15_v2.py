with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Animal purchase gate: Day 10 cutoff, plus Day 11 Affluent Expansion Gate (budget >= 8000)
old_animal_gate = """    for animal in ("COW", "SHEEP"):
        # Day-10 Amortization Horizon: Never buy animals after Day 10 (cows take 8+ days to yield!)
        if day > 10: break"""

new_animal_gate = """    for animal in ("COW", "SHEEP"):
        # Amortization Horizon: Hard cutoff after Day 10, with Day-11 Affluent Gate (budget >= 8000) for peak ceiling!
        if day > 11: break
        if day == 11 and budget < 8000: break"""
assert old_animal_gate in code, "old_animal_gate not found"
code = code.replace(old_animal_gate, new_animal_gate)

# 2. Fertilizer reserve optimization: cap reserve at min(6, len(_fertilizer_positions(obs)))
old_fert_reserve = """    # If strawberry price < 60, fertilizing strawberries has lower ROI than selling fertilizer at $40-$50!
    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""

new_fert_reserve = """    # Active Fertilizer Monetization: reserve up to 6 for active fertilization, monetize all excess!
    fert_reserve = min(fertilizer, min(6, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0
    fert_sale = max(0, fertilizer - fert_reserve)
    if fert_sale > 0:
        orders.append(["SELL", "FERTILIZER", fert_sale])
        budget += fert_sale * p_fert * 0.95
        _MATCH_LEDGER["fertilizer_revenue"] += fert_sale * p_fert * 0.95"""
assert old_fert_reserve in code, "old_fert_reserve not found"
code = code.replace(old_fert_reserve, new_fert_reserve)

# 3. Wheat feed buffer: 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))
old_wheat_buf = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)"""
new_wheat_buf = """    # Day 28-29 Wheat Liquidation: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29!
    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""
assert old_wheat_buf in code, "old_wheat_buf not found"
code = code.replace(old_wheat_buf, new_wheat_buf)

# 4. Quadrant protection for fertilizer collection: high friction for other quadrants so crop workers never wander
old_friction = """                # Routine chores prefer local quadrant (tie-breaker friction = 2 turns)
                friction = 2.0 if task[4] in ("water", "dig", "plant", "fertilizer") and _quadrant(task[1]) != q_u else 0.0"""

new_friction = """                # Routine chores prefer local quadrant; pasture fertilizer collection strictly local (friction = 8 turns)
                friction = (8.0 if task[4] == "fertilizer" else 2.0) if task[4] in ("water", "dig", "plant", "fertilizer") and _quadrant(task[1]) != q_u else 0.0"""
assert old_friction in code, "old_friction not found"
code = code.replace(old_friction, new_friction)

# Also boost COLLECT_FERTILIZER EV slightly for local pasture workers (from p_fert * 0.95 to p_fert * 1.2)
old_fert_task = 'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))'
new_fert_task = 'tasks.append(_task(3, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.2))'
assert old_fert_task in code, "old_fert_task not found"
code = code.replace(old_fert_task, new_fert_task)

with open(r"D:\kaggriculture\scratch\candidate_rc15_v2.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created candidate_rc15_v2.py cleanly!")
