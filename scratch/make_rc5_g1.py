with open(r"D:\kaggriculture\submission_rc4_2_hybrid.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Animal site active: NW from Day 0
target_pasture = """def _animal_site_active(pos, day, unlocked):
    \"\"\"Stage livestock growth so labour and feed can grow before the herd.\"\"\"
    x, y = pos
    if x < 5 and y < 5:
        return day >= 4"""

repl_pasture = """def _animal_site_active(pos, day, unlocked):
    \"\"\"Stage livestock growth so labour and feed can grow before the herd.\"\"\"
    x, y = pos
    if x < 5 and y < 5:
        return True"""
assert target_pasture in code, "Target pasture snippet not found"
code = code.replace(target_pasture, repl_pasture)

# 2. DEFAULT_STRATEGY opening settings
target_strat = """    'opening_animals': 0,
    'opening_carrots': 2,
    'opening_cows': None,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 9,
    'opening_sheep': None,
    'opening_wheat': 10,"""

repl_strat = """    'opening_animals': 3,
    'opening_carrots': 2,
    'opening_cows': 2,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 4,
    'opening_sheep': 1,
    'opening_wheat': 12,"""
assert target_strat in code, "Target strategy snippet not found"
code = code.replace(target_strat, repl_strat)

# 3. Labor scaling
target_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    # Base labor ramp: smooth early ramp to prevent wage shock
    if day == 0: return 2
    if day == 1: return 2
    if day <= 3: return 3
    if day <= 6: return 5
    if day <= 9: return 7
    if day <= 14: return 9
    if day <= 28: return 11
    return 6"""

repl_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 2: return 4
    if day <= 5: return 5
    if day <= 8: return 7
    if day <= 14: return 9
    if day <= 28: return 11
    return 6"""
assert target_labor in code, "Target labor snippet not found"
code = code.replace(target_labor, repl_labor)

# Critical target
target_crit = """    critical_target = min(target_hires, 2 if day <= 1 else 3 if day <= 4 else 5 if day <= 8 else 8 if day <= 14 else 10)"""
repl_crit = """    critical_target = min(target_hires, 4 if day <= 2 else 5 if day <= 5 else 7 if day <= 8 else 9 if day <= 14 else 11)"""
assert target_crit in code, "Target critical labor snippet not found"
code = code.replace(target_crit, repl_crit)

# 4. Feed wheat buffer: 2 days buffer
target_feed = """    if wheat_total < animal_count and day < 28:
        feed_needed = animal_count - wheat_total"""
repl_feed = """    if wheat_total < animal_count * 2 and day < 28:
        feed_needed = animal_count * 2 - wheat_total"""
assert target_feed in code, "Target feed snippet not found"
code = code.replace(target_feed, repl_feed)

# 5. Land expansion: day >= 6 with $500 reserve for NE, day >= 9 for SW
target_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 500 if day <= 10 else 1000
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 9 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""
assert target_land in code, "Target land snippet not found"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc5_g1.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc5_g1.py successfully!")
