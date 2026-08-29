"""Build script to create the standalone submission_bugfix.py file from submission_clean.py.

Applies solely the surgical Step-696 bugfix (preserving valid HIRE orders alongside liquidation sells).
Keeps submission.py (Control A 🧊) completely pristine.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
clean_file = os.path.join(BASE_DIR, "submission_clean.py")
target_file = os.path.join(BASE_DIR, "submission_bugfix.py")

with open(clean_file, "r", encoding="utf-8") as f:
    content = f.read()

target_block = """        # End of game clearance (steps >= 696, beginning of Day 30): force sell everything to avoid deadweight loss
        if step >= 696:
            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            if clean_orders:
                act["market"] = clean_orders
            return act"""

replacement_block = """        # End of game clearance (steps >= 696, beginning of Day 30):
        # BUG FIX: Preserve core schedule's valid orders (including HIREs) and merge liquidation sells up to 10-order limit
        if step >= 696:
            merged_orders = []
            # 1. Prioritize liquidation sells for remaining shed stock to avoid deadweight inventory
            if straw_in_shed > 0: merged_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: merged_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: merged_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            # 2. Fill remaining available order slots with valid core schedule orders (e.g. HIRE)
            for m in market_orders:
                if len(merged_orders) >= 10:
                    break
                if isinstance(m, (list, tuple)) and len(m) >= 1:
                    # Avoid duplicate sell commands for the same item
                    if len(m) >= 2 and m[0] == "SELL" and any(len(x) >= 2 and x[0] == "SELL" and x[1] == m[1] for x in merged_orders):
                        continue
                    merged_orders.append(m)
            act["market"] = merged_orders[:10]
            return act"""

if target_block not in content:
    print("ERROR: Target block not found in submission_clean.py!")
    sys.exit(1)

fixed_content = content.replace(target_block, replacement_block, 1)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(fixed_content)

print(f"Successfully built standalone: {target_file}")
print(f"Size: {len(fixed_content)} chars / {len(fixed_content.splitlines())} lines")
