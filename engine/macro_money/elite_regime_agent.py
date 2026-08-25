"""Track B (Candidate EXP051): Conditional Elite-Regime Specialized Agent.
Maintains 100.0% pure Variant D.1 execution on all Standard and Low-Liquidity Crash seeds.
In Elite-Pie seeds (classified on Days 0-5 from Town Shop Demand Depth):
  - Extends Strawberry Replant Horizon from Day 18 to Day 20 (generating a 5th harvest wave).
  - Maximizes labor throughput for the larger market absorption capacity.
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

class EarlyRegimeClassifier:
    """Classifies whether the current seed is an Elite Market-Pie seed on Steps 0-120."""
    def __init__(self):
        self.is_elite = False
        self.classified = False
        self.cumulative_town_demand = 0.0

    def reset(self):
        self.is_elite = False
        self.classified = False
        self.cumulative_town_demand = 0.0

    def update(self, obs: Dict[str, Any]) -> bool:
        if self.classified:
            return self.is_elite

        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        market = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        town_orders = market.get("orders") or []

        # Accumulate town shop demand depth across Steps 0-120
        for o in town_orders:
            if len(o) >= 3 and o[0] == "BUY": # Town shop buying from players
                qty = float(o[2])
                self.cumulative_town_demand += qty

        if step >= 120:
            self.classified = True
            # Elite seeds exhibit > 350 units of town purchase demand by Step 120
            self.is_elite = (self.cumulative_town_demand >= 350.0)

        return self.is_elite

class EliteRegimeSpecializedAgent:
    """Agent that switches to Elite-Basin parameters only in verified Elite regimes."""
    def __init__(self):
        self.classifier = EarlyRegimeClassifier()

    def reset(self):
        self.classifier.reset()

    def act(self, obs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        is_elite = self.classifier.update(obs)

        # 1. Non-Elite (Standard or Crash): 100.0% Pure Frozen D.1 Execution
        if not is_elite:
            return apex4_mod.agent(obs, config)

        # 2. Elite Regime Basin: Extended Replanting on Days 18-20 for 5th Wave
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        money = float(own_farm.get("money", 0))
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict):
            return base_act

        orders = list(base_act.get("market") or [])

        # In Elite regime on Days 18-20 with ample cash (>= $5,000), buy seeds for the 5th wave
        if 18 <= day <= 20 and money >= 5000.0 and int(shed.get("STRAWBERRY_SEED", 0)) < 16:
            if not any(len(o) >= 2 and o[0] == "BUY_SEED" and o[1] == "STRAWBERRY" for o in orders):
                if len(orders) < 10:
                    orders.append(["BUY_SEED", "STRAWBERRY", 16])

        return {
            "farmer": base_act.get("farmer"),
            "hands": base_act.get("hands"),
            "market": orders[:10],
        }

_GLOBAL_ELITE_AGENT = EliteRegimeSpecializedAgent()

def agent(obs, configuration=None):
    global _GLOBAL_ELITE_AGENT
    return _GLOBAL_ELITE_AGENT.act(obs, configuration)
