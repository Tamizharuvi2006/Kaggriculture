with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# Priority and EV boost for COLLECT_FERTILIZER: priority 2, EV p_fert * 1.5
old_fert_task = 'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))'
new_fert_task = 'tasks.append(_task(2, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.5))'
assert old_fert_task in code, "old_fert_task not found"
code = code.replace(old_fert_task, new_fert_task)

with open(r"D:\kaggriculture\scratch\candidate_rc15_fert_boost.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created scratch/candidate_rc15_fert_boost.py successfully!")
