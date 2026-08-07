"""V8.2 Experimental Agent — Phase 2: Adaptive SE Expansion Only.

Architecture:
  submission_v82_exp.py
      ↓
  world_state.evaluate_world_state(obs)
      ↓
  Adaptive SE Expansion Logic:
    If day >= 11 and money >= $3,500 and occupancy >= 70% and feed_runway >= 1.5 days:
        Enable SE expansion (unlock_se = True)
      ↓
  v18_mod.configure_strategy(DYNAMIC_STRATEGY)
      ↓
  v18_mod.agent(obs)
"""

import sys
import os
import importlib.util

sys.path.insert(0, r"C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r"D:\kaggleculture_repo\kaggleculture-main\reference")

from world_state import evaluate_world_state

# Load V18 execution engine
v18_path = r"D:\kaggleculture_repo\kaggleculture-main\reference\kaitofukami-v18.py"
spec = importlib.util.spec_from_file_location("v18_v82_ref", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

# Base V8.1 Strategy
BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def agent(obs, config=None):
    """V8.2 Experimental Agent Entrypoint — Phase 2 (Adaptive SE Expansion)."""
    strategy = dict(BASE_STRATEGY)

    try:
        # 1. Evaluate World State
        state = evaluate_world_state(obs)
        day = state["day"]
        money = state["money"]
        occupancy = state["occupancy_ratio"]
        feed_runway = state["feed_runway_days"]

        # 2. Phase 2: Adaptive SE Expansion Gating
        # Unlock SE land ONLY IF: day >= 11, money >= $3,500, occupancy >= 70%, feed_runway >= 1.5
        if day >= 11 and money >= 3500 and occupancy >= 0.70 and feed_runway >= 1.5:
            strategy["land_se_day"] = day
    except Exception:
        pass

    # 3. Configure strategy and execute via V18 engine
    v18_mod.configure_strategy(strategy)
    return v18_mod.agent(obs)
