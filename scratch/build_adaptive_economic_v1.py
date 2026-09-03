import os

# Build candidates/submission_adaptive_economic_v1.py cleanly
with open(r"D:\kaggriculture\baseline\kaitofukami-v18.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. Header and constants (lines 0 to 41)
header = """\"\"\"Kaggriculture Adaptive Economic Agent — V1 Clean Production Architecture.

Clean, 100% Observation-Driven Controller:
- Zero Tape / Zero Replay Dependency: Removed _V18_RUNTIME_B85 and fixed schedules.
- Decoupled Brain & Hands: Physical worker pathfinding, daily watering, and shed logistics
  are managed by the native task dispatcher (_assign_actions).
- Dynamic Economic Planner:
  * Unit-Margin Livestock Guard (2 cows maximum, eliminating the $40k open-market feed bleed).
  * Dynamic Crop Allocation: Evaluates Marginal Return per Tile-Day (MR/TD).
  * On-Farm Wheat Production: Allocates dedicated tiles to Wheat seeds ($1.67/feed vs $45 market)
    when market wheat is expensive, feeding livestock for pennies and selling surplus into town shops.
  * Accelerated Land Expansion: Unlocks Quadrant 2 & 3 as soon as capital permits.
\"\"\"
from __future__ import annotations

import math

"""

constants = "".join(lines[15:41])

with open(r"D:\kaggriculture\scratch\full_strategy.py") as sf:
    strategy_block = "\n" + sf.read() + "\n"

# Extract helper functions from line 2284 to 4388 (the actual engine code)
engine_code = "".join(lines[2284:4388])

# New, clean agent entry point without any tape playback
agent_entry = """

def agent(obs):
    \"\"\"Kaggle competition entry point — 100% Observation-Driven Controller.\"\"\"
    try:
        _observe_opponent(obs)
        unit_actions = _assign_actions(obs)
        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": _market_orders(obs),
        }
    except Exception as e:
        return {"farmer": ["PASS"], "hands": [], "market": []}
"""

full_code = header + constants + strategy_block + engine_code + agent_entry

target_path = r"D:\kaggriculture\candidates\submission_adaptive_economic_v1.py"
with open(target_path, "w", encoding="utf-8") as f:
    f.write(full_code)

print(f"[+] Successfully built {target_path}: {len(full_code):,} chars, {len(full_code.splitlines())} lines.")
