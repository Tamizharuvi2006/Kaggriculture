with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add the Day-10 Hard Animal Cutoff to RC6-D.1
target_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""

repl_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        # Day-10 Amortization Horizon: Never buy animals after Day 10 (cows take 8+ days to yield!)
        if day > 10: break
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""
assert target_loop in code, "Target loop not found"
code = code.replace(target_loop, repl_loop)

with open(r"D:\kaggriculture\submission_rc12.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc12.py successfully!")
