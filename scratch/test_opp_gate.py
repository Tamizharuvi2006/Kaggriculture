import os, sys, json
import kaggle_environments

with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    rc6_code = f.read()

# Modify animal purchase loop in RC6_D1:
target = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):"""

replacement = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    opp_money = float(_get(_get(obs, "farms", [])[1 - player], "money", 0))
    for animal in ("COW", "SHEEP"):
        # Armored Floor Protection: Never buy animals after Day 10 if rival is hyper-affluent (market dump risk)
        if day > 10 and opp_money > 8000: break"""

assert target in rc6_code
test_code = rc6_code.replace(target, replacement)

sys.path.insert(0, r"D:\kaggriculture")
from scratch.eval_harness import evaluate_variant

if __name__ == "__main__":
    scores = evaluate_variant(test_code, "rc6_opp_gate")
    for i, s in enumerate(scores):
        print(f"#{i+1:02d}: ${s:>6,d}")
