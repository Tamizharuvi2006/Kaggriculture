with open(r"D:\kaggriculture\submission_rc6_d.py", "r", encoding="utf-8") as f:
    code = f.read()

target_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 9 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 1200 if day <= 10 else 1000
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 9 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""
assert target_land in code, "Target land snippet not found"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc6_e.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc6_e.py successfully!")
