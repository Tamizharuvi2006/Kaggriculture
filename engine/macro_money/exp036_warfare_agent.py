"""Track B (Candidate EXP036): Opponent Warfare Agent.
Wired with OpponentDependencyDetector on top of the mature APEX physical executor.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib.util

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.macro_money.opponent_detector import OpponentDependencyDetector

class OpponentWarfareAgent:
    """Candidate EXP036: Opponent Dependency & Asymmetric Market Pressure Agent."""
    def __init__(self):
        self.market_tracker = MarketTracker()
        self.detector = OpponentDependencyDetector()

    def reset(self):
        self.market_tracker.reset()
        self.detector = OpponentDependencyDetector()

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)

            # 1. Flawless Physical Substrate Execution
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            base_orders = list(base_act.get("market") or [])

            # 2. Opponent-Relative Market Priority Allocation
            market_orders = self.detector.prioritize_orders(farm, market, obs, base_orders)

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders,
            }
        except Exception:
            return apex4_mod.agent(raw_obs, raw_config)

# Singleton entry point
_GLOBAL_WARFARE = OpponentWarfareAgent()

def agent(obs, configuration=None):
    global _GLOBAL_WARFARE
    return _GLOBAL_WARFARE.act(obs, configuration)
