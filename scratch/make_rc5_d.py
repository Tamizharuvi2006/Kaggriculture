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

# 2. Land Readiness: Prevent Day 0-4 capital trap, expand Day 5+ with feed safety and $350 buffer
target_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    # RC5-D Land Readiness: Expand when opening crops clear (Day >= 5) and operating buffer is safe
    land_cost = 0
    land_reserve_ne = 350
    land_reserve_sw = 800
    feed_safe = (wheat_total >= animal_count * 2) or (animal_count == 0) or (day >= 20)
    if len(unlocked) == 1 and day >= 5 and "NE" not in unlocked and feed_safe and budget >= 1000 + land_reserve_ne:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 8 and "SW" not in unlocked and feed_safe and budget >= 2000 + land_reserve_sw:
        land_cost = 2000"""

assert target_land in code, "Target land snippet not found!"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc5_d.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc5_d.py successfully!")
