"""Challenger population bots representing distinct ladder meta archetypes."""
from __future__ import annotations
import sys
import os
import copy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib.util

spec = importlib.util.spec_from_file_location("base_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
base_v83 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_v83)

def carrot_rusher_agent(obs, config=None):
    """Archetype A: Aggressive Carrot Rusher (44.2% ladder population)."""
    act = base_v83.agent(obs, config)
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    day = step // 24
    
    # Overrides market orders to aggressively buy carrot seeds
    if isinstance(act, dict) and "market" in act:
        market_orders = list(act["market"])
        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
        money = float(farms[0].get("money", 0)) if farms else 0.0
        
        if 2 <= day <= 24 and money >= 200.0:
            if not any(len(m) >= 2 and m[0] == "BUY_SEED" and m[1] == "CARROT" for m in market_orders):
                if len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "CARROT", 6])
        act["market"] = market_orders
    return act

def livestock_rusher_agent(obs, config=None):
    """Archetype B: Livestock Heavy Rusher (Cow/Sheep maximalist)."""
    act = base_v83.agent(obs, config)
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    day = step // 24
    
    if isinstance(act, dict) and "market" in act:
        market_orders = list(act["market"])
        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
        money = float(farms[0].get("money", 0)) if farms else 0.0
        
        if day <= 8 and money >= 500.0 and len(market_orders) < 10:
            if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" for m in market_orders):
                market_orders.append(["BUY_ANIMAL", "COW", 1])
        act["market"] = market_orders
    return act
