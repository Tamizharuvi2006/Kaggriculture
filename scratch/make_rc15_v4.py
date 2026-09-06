with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Day-gated manure collection: Priority 4 before Day 10 (protects opening melon watering), Priority 2 after Day 10 (unlocks herd care synergy and $91k ceiling)
old_fert_task = 'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))'
new_fert_task = """if day <= 10:
                        tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))
                    else:
                        tasks.append(_task(2, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.2))"""
assert old_fert_task in code, "old_fert_task not found"
code = code.replace(old_fert_task, new_fert_task)

# 2. Wheat feed buffer: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29
old_wheat_buf = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)"""
new_wheat_buf = """    # Day 28-29 Wheat Liquidation: safe 2-day buffer during season, 1-day buffer on Day 28, 0 on Day 29!
    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""
assert old_wheat_buf in code, "old_wheat_buf not found"
code = code.replace(old_wheat_buf, new_wheat_buf)

with open(r"D:\kaggriculture\scratch\candidate_rc15_v4.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created candidate_rc15_v4.py cleanly!")
