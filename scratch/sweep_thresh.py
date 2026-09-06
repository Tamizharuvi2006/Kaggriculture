import os, sys, json
import kaggle_environments

sys.path.insert(0, r"D:\kaggriculture")
from scratch.eval_harness import evaluate_variant

if __name__ == "__main__":
    with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
        rc6_code = f.read()

    target = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):"""

    for thresh in [150, 160, 170, 180]:
        repl = f"""    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    opp_money = float(_get(_get(obs, "farms", [])[1 - player], "money", 0))
    for animal in ("COW", "SHEEP"):
        # Armored Horizon Gate:
        if day > 10:
            p_check = float(prices.get("MILK" if animal == "COW" else "WOOL", 0) or 0)
            if opp_money > 8000 or p_check < {thresh}:
                continue"""
        code = rc6_code.replace(target, repl)
        print(f"\n--- Testing Threshold {thresh} ---")
        evaluate_variant(code, f"thresh_{thresh}")
