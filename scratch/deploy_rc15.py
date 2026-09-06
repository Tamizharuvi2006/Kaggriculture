import os, sys

with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    rc6_code = f.read()

target1 = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):"""

repl1 = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    opp_money = float(_get(_get(obs, "farms", [])[1 - player], "money", 0))
    for animal in ("COW", "SHEEP"):
        # Armored Horizon Gate: Never buy animals after Day 10 if rival has > $8,000 cash (market dump risk)
        if day > 10 and opp_money > 8000: break"""

target2 = """    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)"""
repl2 = """    # Two-Stage Graduated Wheat Liquidation (Day 28: 1 feed buffer, Day 29: full liquidation)
    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""

assert target1 in rc6_code, "Target 1 not found"
assert target2 in rc6_code, "Target 2 not found"

champion_code = rc6_code.replace(target1, repl1).replace(target2, repl2)

with open(r"D:\kaggriculture\submission_rc15.py", "w", encoding="utf-8") as f:
    f.write(champion_code)
print("Successfully written submission_rc15.py")

with open(r"D:\kaggriculture\submission.py", "w", encoding="utf-8") as f:
    f.write(champion_code)
print("Successfully updated submission.py with new champion")
