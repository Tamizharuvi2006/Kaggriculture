"""V8.1 Baseline Autonomous Agent ($121,973.63 Verified 100-Match Baseline).

Runs independently by loading kaitofukami-v18.py from the baseline directory
and configuring Strategy 15 parameter overrides (Cows = 12).
"""

import sys
import os
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

# Load kaitofukami-v18.py relative to baseline directory
v18_path = os.path.join(os.path.dirname(__file__), "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_baseline_mod", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

# Strategy 15 Parameter Overrides ($121,973.63 100-Match Verified Baseline)
STRATEGY_15_OVERRIDES = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}

v18_mod.configure_strategy(STRATEGY_15_OVERRIDES)


def agent(obs, config=None):
    """Entrypoint for Kaggle Environment."""
    return v18_mod.agent(obs)
