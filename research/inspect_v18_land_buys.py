import os
import sys
import importlib.util

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")

spec = importlib.util.spec_from_file_location("mod_v18", base_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

runtime = getattr(mod, "_V18_RUNTIME")
for bname, bdata in runtime["experts"].items():
    actions = bdata["actions"]
    print(f"--- Expert: {bname} ---")
    for s, act in enumerate(actions):
        market = act.get("market", [])
        for m in market:
            if isinstance(m, (list, tuple)) and len(m) > 0 and m[0] == "BUY_LAND":
                print(f"  Step {s:3d} (Day {s//24+1:2d}): BUY_LAND")
