"""Script to generate submission_candidate_apex36.py from submission_candidate_apex35.py with exact surgical insertion."""

import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(base_dir, "generalization_pipeline", "submission_candidate_apex35.py")
dst_path = os.path.join(base_dir, "generalization_pipeline", "submission_candidate_apex36.py")

with open(src_path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace header comment
old_header = "# APEX 3.5 MONOLITHIC STANDALONE TOURNAMENT ENGINE (DUAL-REGIME LIQUIDITY PRIORITY & GENTLE REBOUND)"
new_header = "# APEX 3.6 SEAT-CONDITIONED DUAL-REGIME TOURNAMENT ENGINE (6-GATE VALIDATED)"
code = code.replace(old_header, new_header, 1)

# Target injection point in agent() function right before Enforce 3-quadrant ceiling
target = "        # Enforce 3-quadrant ceiling"
injection = """        # SEAT-CONDITIONED DUAL-REGIME PREEMPTION (APEX 3.6 - PHASE 105 VALIDATED):
        # Seat 1: Advance shed preemption on Turn 22 captures un-slipped town demand ahead of Seat 0
        player_idx = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        if player_idx == 1 and (step % 24 == 22):
            if straw_in_shed > 0 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                market_orders.append(["SELL", "MILK", milk_in_shed])

        # Enforce 3-quadrant ceiling"""

code = code.replace(target, injection, 1)

with open(dst_path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Created {dst_path} successfully. Total characters: {len(code)}")
