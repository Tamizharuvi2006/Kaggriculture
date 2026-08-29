"""Builder for standalone Kaggle submission file submission_adaptive_d2.py."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
clean_file = os.path.join(BASE_DIR, "submission_clean.py")
target_file = os.path.join(BASE_DIR, "submission_adaptive_d2.py")

with open(clean_file, "r", encoding="utf-8") as f:
    code = f.read()

# Replace header description
code = code.replace(
    '"""Clean Production Standalone Tournament Agent (Variant D.1).',
    '"""Adaptive Production Standalone Tournament Agent (Variant D.2 Adaptive).'
)

# Insert the validated adaptive enhancements into agent() function
old_block = """        # Enforce 3-quadrant ceiling
        final_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(m)
        act["market"] = final_orders

        return act"""

new_block = """        # Enforce 3-quadrant ceiling
        final_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(m)

        # ============================================================================================
        # VALIDATED ADAPTIVE ENHANCEMENTS (D.2):
        # 1. Milk & Strawberry Collapse Defenses on Days 26-29 (Steps 600-695)
        # ============================================================================================
        if 600 <= step < 696:
            # Milk Defense: Days 26-29, p_milk <= $95.0 -> immediate liquidation
            if p_milk <= 95.0 and milk_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in final_orders):
                    final_orders.append(["SELL", "MILK", milk_in_shed])

            # Strawberry Defense: Days 27-29, p_straw <= $125.0 -> early liquidation
            if step >= 624 and p_straw <= 125.0 and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in final_orders):
                    final_orders.append(["SELL", "STRAWBERRY", straw_in_shed])

        # ============================================================================================
        # 2. Day-30 Emergency Labor Burst (+6 HIRE at D30H00)
        # ============================================================================================
        day = (step // 24) + 1
        hour = step % 24
        if day == 30 and hour == 0:
            slots = max(0, 10 - len(final_orders))
            for _ in range(min(6, slots)):
                final_orders.append(["HIRE"])

        act["market"] = final_orders[:10]

        return act"""

assert old_block in code, "Target code block not found in submission_clean.py"
code_d2 = code.replace(old_block, new_block)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(code_d2)

print(f"Successfully generated standalone {target_file} ({len(code_d2.splitlines())} lines, {len(code_d2)} bytes)")
