import json
import os
import sys

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")

with open(base_path, "r", encoding="utf-8") as f:
    code = f.read()

# Let's inspect the actions in _V18_RUNTIME
import importlib.util
spec = importlib.util.spec_from_file_location("mod_v18", base_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

runtime = getattr(mod, "_V18_RUNTIME")
board_name = runtime["board_by_seat"]["0"]
actions = runtime["experts"][board_name]["actions"]

print(f"Board: {board_name}")
for step in range(0, 169):
    act = actions[step]
    market = act.get("market", [])
    if market:
        print(f"Step {step:3d} (Day {step//24+1}): {market}")
