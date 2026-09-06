with open(r"D:\kaggriculture\submission_rc4_2_hybrid.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Pasture gate: NW active from Day 0
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

assert target_pasture in code, "Target pasture snippet not found!"
code = code.replace(target_pasture, repl_pasture)

# 2. RC5-E Land Readiness: day >= 4 for NE (prevents Day 0-3 trap), day >= 8 for SW, land_reserve = 500
target_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    # RC5-E: Allow NE from Day 4 (prevents Day 0-3 capital trap) and SW from Day 8 with $500 reserve
    land_cost = 0
    land_reserve = 500 if day <= 10 else 1000
    if len(unlocked) == 1 and day >= 4 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 8 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

assert target_land in code, "Target land snippet not found!"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc5_e.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc5_e.py successfully!")
