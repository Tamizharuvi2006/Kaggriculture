with open(r"D:\kaggriculture\submission_rc6_b.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Workforce ramp: scale up to 12 workers from Day 12 to Day 28
target_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 1: return 4
    if day <= 4: return 5
    if day <= 8: return 7
    if day <= 14: return 9
    if day <= 28: return 11
    return 6"""

repl_labor = """def _hire_target(day):
    \"\"\"Dynamic labor requirement sized to active workload (plants + animals).\"\"\"
    if day <= 1: return 4
    if day <= 4: return 5
    if day <= 7: return 7
    if day <= 11: return 9
    if day <= 28: return 12
    return 6"""
assert target_labor in code, "Target labor snippet not found"
code = code.replace(target_labor, repl_labor)

# Critical target
target_crit = """    critical_target = min(target_hires, 4 if day <= 1 else 5 if day <= 4 else 7 if day <= 8 else 9 if day <= 14 else 11)"""
repl_crit = """    critical_target = min(target_hires, 4 if day <= 1 else 5 if day <= 4 else 7 if day <= 7 else 9 if day <= 11 else 12)"""
assert target_crit in code, "Target critical labor snippet not found"
code = code.replace(target_crit, repl_crit)

# 2. Animal harvest & care EV
target_animal_tasks = """                if int(tile.get("yield_units", 0)) > 0:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = int(tile.get("yield_units", 1)) * p_unit * 0.95
                    tasks.append(_task(1, (x, y), ["HARVEST"], None, "harvest", ev))
                if not tile.get("cared_today", False) and day < 29:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = p_unit * 0.95
                    tasks.append(_task(2, (x, y), ["CARE"], None, "care", ev))"""

repl_animal_tasks = """                if int(tile.get("yield_units", 0)) > 0:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = int(tile.get("yield_units", 1)) * p_unit * 1.5
                    tasks.append(_task(1, (x, y), ["HARVEST"], None, "harvest", ev))
                if not tile.get("cared_today", False) and day < 29:
                    p_unit = p_milk if anim == "COW" else p_wool
                    ev = p_unit * 1.5
                    tasks.append(_task(2, (x, y), ["CARE"], None, "care", ev))"""
assert target_animal_tasks in code, "Target animal tasks snippet not found"
code = code.replace(target_animal_tasks, repl_animal_tasks)

with open(r"D:\kaggriculture\submission_rc6_c.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc6_c.py successfully!")
