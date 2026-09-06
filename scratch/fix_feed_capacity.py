with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace animal gate with Feed Carrying Capacity Gate using farm.get("tiles", [])
old_animal_gate = """    for animal in ("COW", "SHEEP"):
        # Day-10 Amortization Horizon: Never buy animals after Day 10 (cows take 8+ days to yield!)
        if day > 10: break"""

new_animal_gate = """    # Calculate farm feed carrying capacity (1 wheat plot reliably supports 1.5 animals)
    tiles = farm.get("tiles", [])
    wheat_plots = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
    current_herd = counts["COW"] + counts["SHEEP"]
    max_carrying_capacity = max(4, int(wheat_plots * 1.5))

    for animal in ("COW", "SHEEP"):
        # Amortization Horizon: Hard cutoff after Day 11.
        if day > 11: break
        # On Day 11: Only expand herd if farm has established feed carrying capacity and affluent budget!
        if day == 11:
            if budget < 5000 or current_herd >= max_carrying_capacity:
                break"""
assert old_animal_gate in code, "old_animal_gate not found"
code = code.replace(old_animal_gate, new_animal_gate)

# Add Day 28-29 Wheat Liquidation
old_wheat_buf = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)"""
new_wheat_buf = """    # Day 28-29 Wheat Liquidation: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29!
    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""
assert old_wheat_buf in code, "old_wheat_buf not found"
code = code.replace(old_wheat_buf, new_wheat_buf)

with open(r"D:\kaggriculture\scratch\candidate_rc15_feed_capacity.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed candidate_rc15_feed_capacity.py cleanly!")
