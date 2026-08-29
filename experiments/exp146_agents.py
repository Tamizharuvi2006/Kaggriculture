"""EXP146 Agent Definitions: Cash Runway Threshold Sweep for Adaptive Wheat Retention."""
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

def agent_arm_a(obs, config=None):
    """Arm A: Exact D.1 Baseline Control."""
    return sub_d1.agent(obs, config)

def make_runway_gated_agent(min_runway_days: float):
    """Creates an agent that retains wheat only when cash runway >= min_runway_days."""
    def agent_fn(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = step // 24
        act = sub_d1.agent(obs, config)

        if not isinstance(act, dict) or "market" not in act:
            return act

        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_f = farms[player] if len(farms) > player else {}
        money = float(own_f.get("money") or 0.0)
        shed = own_f.get("inventory") or {}
        wheat_in_shed = int(shed.get("WHEAT", 0))

        # Calculate active workers & animals for daily burn rate
        hands = act.get("hands") or []
        w_count = max(1, len(hands))

        tiles = own_f.get("tiles", []) or []
        cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
        sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
        daily_feed_demand = cows + sheep

        # Daily burn rate = Wages ($100/worker/day) + Feed ($40/animal/day) + Overhead ($100/day)
        daily_burn = (w_count * 100.0) + (daily_feed_demand * 40.0) + 100.0
        current_runway = money / daily_burn if daily_burn > 0 else 0.0

        market_info = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = market_info.get("prices", {}) if isinstance(market_info, dict) else getattr(market_info, "prices", {}) or {}
        p_wheat = float(prices.get("WHEAT", 20.0))
        p_milk = float(prices.get("MILK", 120.0))
        p_fert = float(prices.get("FERTILIZER", 50.0))

        remaining_days = max(0, 30 - day)
        downstream_val = (0.5 * p_milk) + p_fert if daily_feed_demand > 0 and remaining_days >= 2 else 0.0
        feed_buffer = daily_feed_demand * min(4, remaining_days)

        market_orders = list(act.get("market") or [])
        new_orders = []

        for order in market_orders:
            if isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL" and order[1] == "WHEAT":
                # Only allow retention if Runway >= min_runway_days AND Downstream Value > P_WHEAT AND Day <= 25
                if current_runway >= min_runway_days and downstream_val > p_wheat and day <= 25 and feed_buffer > 0:
                    if wheat_in_shed > feed_buffer:
                        excess = wheat_in_shed - feed_buffer
                        if excess > 0:
                            new_orders.append(["SELL", "WHEAT", excess])
                    # If shed <= feed_buffer, order is suppressed (retained!)
                else:
                    # Low runway, terminal window, or price parity: liquidate wheat for liquidity!
                    new_orders.append(order)
            else:
                new_orders.append(order)

        # Force terminal clearance on Step 696+ (Day 30)
        if step >= 696 and wheat_in_shed > 0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "WHEAT" for m in new_orders):
                new_orders.append(["SELL", "WHEAT", wheat_in_shed])

        act["market"] = new_orders
        return act
    return agent_fn

agent_arm_b = make_runway_gated_agent(1.0)
agent_arm_c = make_runway_gated_agent(1.5)
agent_arm_d = make_runway_gated_agent(2.0)
agent_arm_e = make_runway_gated_agent(2.5)
agent_arm_f = make_runway_gated_agent(3.0)
