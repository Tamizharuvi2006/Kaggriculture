with open(r"D:\kaggriculture\submission_rc4_2_hybrid.py", "r", encoding="utf-8") as f:
    code = f.read()

# RC5-F: Keep _animal_site_active 100% UNTOUCHED (day >= 4).
# ONLY modify land expansion timing: allow NE from Day 4 and SW from Day 8 with $500 reserve.
target_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_land = """    # === 4. ACCELERATED LAND EXPANSION (Max 3 Quadrants: NW, NE, SW) ===
    # RC5-F: Allow NE from Day 4 and SW from Day 8 with $500 reserve; _animal_site_active frozen at day >= 4
    land_cost = 0
    land_reserve = 500 if day <= 10 else 1000
    if len(unlocked) == 1 and day >= 4 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 8 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

assert target_land in code, "Target land snippet not found!"
code = code.replace(target_land, repl_land)

with open(r"D:\kaggriculture\submission_rc5_f.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc5_f.py successfully!")
