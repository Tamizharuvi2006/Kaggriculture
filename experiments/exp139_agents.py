"""EXP139 Agent Definitions: Arm A (Control), Arm B (Adaptive Livestock), Arm C (Adaptive Market Response)."""
from __future__ import annotations
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def is_1200plus_regime_triggered(obs) -> bool:
    """Trigger: Day 10-14, Opponent Sheep >= 3, Opponent Cows >= 5, Milk Price Velocity < 0."""
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    day = (step // 24) + 1
    if not (10 <= day <= 14):
        return False

    player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
    opp_idx = 1 - player
    farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
    if len(farms) <= opp_idx:
        return False

    opp_farm = farms[opp_idx]
    tiles = opp_farm.get("tiles", []) or []
    opp_cows = sum(1 for row in tiles for t in row if isinstance(t, dict) and t.get("animal") == "COW")
    opp_sheep = sum(1 for row in tiles for t in row if isinstance(t, dict) and t.get("animal") == "SHEEP")

    if opp_sheep < 3 or opp_cows < 5:
        return False

    # Check milk price velocity
    mkt = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
    prices = mkt.get("prices", mkt.get("current_prices", {})) or {}
    p_milk = float(prices.get("MILK", 100.0) or 100.0)

    # If milk price has dropped below 150 or is falling
    return p_milk < 150.0

def agent_arm_a(obs, config=None):
    """Arm A: Exact D.1 Baseline Control."""
    return sub_d1.agent(obs, config)

def agent_arm_b(obs, config=None):
    """Arm B: Conditional Livestock Response.

    When strong dual-asset opponent detected (Days 10-14, opp_sheep>=3, opp_cows>=5, P_milk falling):
    Re-allocates 2 pasture slots from COW to SHEEP to capture $180 wool stream.
    """
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    day = (step // 24) + 1

    act = sub_d1.agent(obs, config)

    if 10 <= day <= 16 and is_1200plus_regime_triggered(obs):
        # Convert any pending BUY_ANIMAL COW to BUY_ANIMAL SHEEP if we have fewer than 2 sheep
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_farm = farms[player] if len(farms) > player else {}
        tiles = own_farm.get("tiles", []) or []
        own_sheep = sum(1 for row in tiles for t in row if isinstance(t, dict) and t.get("animal") == "SHEEP")

        if own_sheep < 2:
            market_orders = list(act.get("market") or [])
            new_orders = []
            replaced = False
            for m in market_orders:
                if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" and not replaced:
                    new_orders.append(["BUY_ANIMAL", "SHEEP"])
                    replaced = True
                else:
                    new_orders.append(m)
            act["market"] = new_orders

    return act

def agent_arm_c(obs, config=None):
    """Arm C: Conditional Market / Liquidity Response.

    When strong dual-asset opponent detected:
    Does NOT buy sheep; instead accelerates milk and strawberry liquidation:
    - Lowers milk sell threshold to $75.0 (does not hoard milk in falling market).
    - Lowers strawberry sell threshold to $115.0 on Days 18-26 to realize peak value before crash.
    """
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    day = (step // 24) + 1

    act = sub_d1.agent(obs, config)

    if day >= 10:
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_farm = farms[player] if len(farms) > player else {}
        shed = own_farm.get("shed", {}) or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

        mkt = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt.get("prices", mkt.get("current_prices", {})) or {}
        p_milk = float(prices.get("MILK", 100.0) or 100.0)
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

        market_orders = list(act.get("market") or [])

        # 1. Milk Protection: Sell milk immediately if P_milk >= $70 and milk_in_shed >= 2
        if p_milk >= 70.0 and milk_in_shed >= 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                if len(market_orders) < 10:
                    market_orders.append(["SELL", "MILK", milk_in_shed])

        # 2. Strawberry Peak Realization: On Days 18-26, sell if P_straw >= $115 and straw_in_shed >= 2
        if 18 <= day <= 26 and p_straw >= 115.0 and straw_in_shed >= 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                if len(market_orders) < 10:
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])

        act["market"] = market_orders[:10]

    return act
