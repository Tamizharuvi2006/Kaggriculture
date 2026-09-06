with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Target Herd: 8 Cows, 5 Sheep (exact Champion composition)
target_plan = """def _animal_plan():
    return _build_animal_plan(8, 4)"""
repl_plan = """def _animal_plan():
    return _build_animal_plan(8, 5)"""
assert target_plan in code, "Target plan not found"
code = code.replace(target_plan, repl_plan)

# 2. Opening Animals: 3 Cows, 1 Sheep, 7 Melons (exact Champion opening)
target_strat = """    'opening_animals': 2,
    'opening_carrots': 2,
    'opening_cows': 2,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 9,
    'opening_sheep': 0,"""

repl_strat = """    'opening_animals': 4,
    'opening_carrots': 2,
    'opening_cows': 3,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 7,
    'opening_sheep': 1,"""
assert target_strat in code, "Target strat not found"
code = code.replace(target_strat, repl_strat)

# 3. Hard Animal Purchase Cutoff at Day 10 Hour 20
target_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""

repl_animal_loop = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):
        # Strict Amortization Cutoff: Zero animal purchases after Day 10!
        if day > 10 or (day == 10 and hour > 20): break
        needed = max(0, target_counts[animal] - counts[animal])
        if needed <= 0 or remaining_days < 7: continue"""
assert target_animal_loop in code, "Target animal loop not found"
code = code.replace(target_animal_loop, repl_animal_loop)

# 4. Labor curve: ramp to 12 workers by Day 10
target_hire = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 1: return 4
    if day <= 4: return 5
    if day <= 7: return 7
    if day <= 11: return 9
    if day <= 28: return 12
    return 6"""

repl_hire = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 1: return 4
    if day <= 4: return 5
    if day <= 7: return 7
    if day <= 9: return 10
    if day <= 28: return 12
    return 6"""
assert target_hire in code, "Target hire not found"
code = code.replace(target_hire, repl_hire)

# 5. Land expansion reserve: NE at Day 7, SW at Day 10
target_land = """    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 9 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    land_cost = 0
    land_reserve = 400 if day <= 10 else 1000
    if len(unlocked) == 1 and day >= 7 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""
assert target_land in code, "Target land not found"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc11.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc11.py successfully!")
