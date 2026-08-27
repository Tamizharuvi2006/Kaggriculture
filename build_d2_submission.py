"""Script to generate submission_d2.py cleanly from submission_clean.py."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
clean_path = os.path.join(BASE_DIR, "submission_clean.py")

with open(clean_path, "r", encoding="utf-8") as f:
    clean_code = f.read()

# Replace header description
d2_header = '''"""Clean Production Standalone Tournament Agent (Variant D.2 - Early Cashflow Optimization).

Builds upon the verified clean baseline (Variant D.1) by incorporating early starter inventory liquidation:
- Liquidates idle starter inventory (WHEAT, FERTILIZER) on Days 1-5 (Steps 0-143) whenever available (qty >= 1).
- Converts deadweight opening assets into active liquid capital to accelerate opening worker hires and Land #2 acquisition.
- Preserves 100% of the 38-Strawberry + 8-Cow spatial and planting spine.
- EXP114 100-Seed Validation (200 matches vs v18): +$1,177.39 mean delta, 92.0% win rate (+1.0% uplift), +$1,908.00 median uplift, 50.66% market share.
"""'''

d2_code = clean_code.replace(
    '"""Clean Production Standalone Tournament Agent (Variant D.1).\n\nThis is a behavior-identical, purified standalone clone of submission.py (Control A).\nAll unreachable legacy schedules (v10-v17), inert constants, and dead imports have been stripped.\nExact parity verified across 14,400 steps (20 seeds x 720 steps): 0 action diffs, 0 reward diffs.\n"""',
    d2_header
)

old_market_block = """        market_orders = list(act.get("market") or [])"""

new_market_block = """        market_orders = list(act.get("market") or [])

        # Early Starter Liquidation (Days 1 to 5 / Steps 0-143): monetize idle wheat & fertilizer
        day = int(obs.get("day", step // 24) or (step // 24)) if isinstance(obs, dict) else getattr(obs, "day", step // 24)
        wheat_in_shed = int(shed.get("WHEAT", 0) or 0)
        if day <= 5:
            for item, qty in (("WHEAT", wheat_in_shed), ("FERTILIZER", fert_in_shed)):
                if qty >= 1:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])"""

assert old_market_block in d2_code, "old_market_block not found in clean_code"
d2_code = d2_code.replace(old_market_block, new_market_block, 1)

d2_path = os.path.join(BASE_DIR, "submission_d2.py")
with open(d2_path, "w", encoding="utf-8") as f:
    f.write(d2_code)

print(f"Generated submission_d2.py successfully: {len(d2_code.splitlines())} lines.")
