"""Track B (Candidate EXP049): Margin-Aware Risk Controller (MARC).
Maintains 100.0% action parity with Variant D.1 on Steps 0-671.
On Steps 672-720, evaluates observable match margin:
- If AHEAD (margin >= +$1,500) or CONTESTED: Executes 100% pure conservative D.1 Step 696 clearance.
- If BEHIND (margin <= -$1,500): Executes a Single Dense Late Harvest Liquidation on Step 718
  (without premature market flooding on Steps 672-695).
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib.util

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

class MarginAwareRiskController:
    """Margin-aware risk controller for Steps 672-720."""
    def __init__(self, behind_threshold: float = -1500.0):
        self.behind_threshold = behind_threshold
        self.risk_triggers = 0

    def reset(self):
        self.risk_triggers = 0

    def resolve(self, obs: Dict[str, Any], config: Optional[Dict[str, Any]], base_act: Dict[str, Any]) -> Dict[str, Any]:
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)

        # 1. 100.0% Parity for Steps 0-671
        if step < 672:
            return base_act

        # 2. Extract Margin
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        opp_farm = farms[1 - player] if len(farms) > (1 - player) else {}
        
        own_money = float(own_farm.get("money", 0))
        opp_money = float(opp_farm.get("money", 0))
        margin = own_money - opp_money

        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        orders = list(base_act.get("market") or [])

        # 3. Decision Logic:
        # If AHEAD or CONTESTED (margin > behind_threshold) -> Normal D.1 Step 696 Clearance
        # If BEHIND (margin <= behind_threshold) -> Single Dense Late Liquidation on Step 718
        items_to_liquidate = ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT")

        if margin > self.behind_threshold:
            # Conservative D.1 Clearance on Step 696+
            if step >= 696:
                for item in items_to_liquidate:
                    qty = int(shed.get(item, 0) or 0)
                    if qty > 0:
                        if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                            if len(orders) < 10:
                                orders.append(["SELL", item, qty])
        else:
            # BEHIND: Allow workers to keep harvesting late ripe plots and flush ONCE at Step 718
            self.risk_triggers += 1
            if step >= 718:
                for item in items_to_liquidate:
                    qty = int(shed.get(item, 0) or 0)
                    if qty > 0:
                        if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                            if len(orders) < 10:
                                orders.append(["SELL", item, qty])
            elif step >= 696:
                # Do NOT clear early, preserve ripe crops on field for final wave
                pass

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": orders[:10],
        }

class MarginRiskAgent:
    """Agent equipped with the Margin-Aware Risk Controller."""
    def __init__(self, behind_threshold: float = -1500.0):
        self.controller = MarginAwareRiskController(behind_threshold=behind_threshold)

    def reset(self):
        self.controller.reset()

    def act(self, obs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict):
            return base_act
        return self.controller.resolve(obs, config, base_act)

_GLOBAL_MARC = MarginRiskAgent()

def agent(obs, configuration=None):
    global _GLOBAL_MARC
    return _GLOBAL_MARC.act(obs, configuration)
