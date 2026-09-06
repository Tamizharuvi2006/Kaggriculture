with open(r"D:\kaggriculture\submission_rc5_a_early_pasture.py", "r", encoding="utf-8") as f:
    base_code = f.read()

# Variant C1: Remove day gates, keep land_reserve = 800
target_c1 = """    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

repl_c1 = """    land_cost = 0
    land_reserve = 800 if day <= 10 else 1200
    if len(unlocked) == 1 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

assert target_c1 in base_code, "Target snippet not found in base_code!"
c1_code = base_code.replace(target_c1, repl_c1)
with open(r"D:\kaggriculture\submission_rc5_c1_day_gate.py", "w", encoding="utf-8") as f:
    f.write(c1_code)

# Variant C2: Keep day gates, reduce reserve to 200
repl_c2 = """    land_cost = 0
    land_reserve = 200 if day <= 10 else 400
    if len(unlocked) == 1 and day >= 6 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and day >= 10 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

c2_code = base_code.replace(target_c1, repl_c2)
with open(r"D:\kaggriculture\submission_rc5_c2_reserve_200.py", "w", encoding="utf-8") as f:
    f.write(c2_code)

# Variant C3: Remove day gates AND reduce reserve to 200
repl_c3 = """    land_cost = 0
    land_reserve = 200 if day <= 10 else 400
    if len(unlocked) == 1 and "NE" not in unlocked and budget >= 1000 + land_reserve:
        land_cost = 1000
    elif len(unlocked) == 2 and "SW" not in unlocked and budget >= 2000 + land_reserve:
        land_cost = 2000"""

c3_code = base_code.replace(target_c1, repl_c3)
with open(r"D:\kaggriculture\submission_rc5_c3_champion_expansion.py", "w", encoding="utf-8") as f:
    f.write(c3_code)

print("Generated C1, C2, and C3 successfully!")
