"""EXP144 1-Seed Physical Instrumentation Proof: Validating Marginal Wheat-Retention Rule."""
from __future__ import annotations
import os
import sys
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def agent_control(obs, config=None):
    """Arm A: Exact D.1 Baseline Control."""
    return sub_d1.agent(obs, config)

def agent_wheat_retention(obs, config=None):
    """Arm B: D.1 with EXP143 Marginal Wheat-Retention Rule."""
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    day = step // 24
    act = sub_d1.agent(obs, config)

    if not isinstance(act, dict) or "market" not in act:
        return act

    player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
    farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
    own_f = farms[player] if len(farms) > player else {}
    shed = own_f.get("inventory") or {}
    wheat_in_shed = int(shed.get("WHEAT", 0))

    tiles = own_f.get("tiles", []) or []
    cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    daily_feed_demand = cows + sheep

    market_info = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
    prices = market_info.get("prices", {}) if isinstance(market_info, dict) else getattr(market_info, "prices", {}) or {}
    p_wheat = float(prices.get("WHEAT", 20.0))
    p_milk = float(prices.get("MILK", 120.0))
    p_fert = float(prices.get("FERTILIZER", 50.0))

    # Calculate expected downstream processing value per unit of wheat
    remaining_days = max(0, 30 - day)
    downstream_val = (0.5 * p_milk) + p_fert if daily_feed_demand > 0 and remaining_days >= 2 else 0.0

    # Retain buffer for next 4 days of feeding
    feed_buffer = daily_feed_demand * min(4, remaining_days)

    market_orders = list(act.get("market") or [])
    new_orders = []

    for order in market_orders:
        if isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL" and order[1] == "WHEAT":
            qty = int(order[2])
            if day >= 26 or downstream_val <= p_wheat or feed_buffer == 0:
                # Terminal window or price parity: sell all wheat
                new_orders.append(order)
            else:
                # Retain feed buffer
                if wheat_in_shed > feed_buffer:
                    excess = wheat_in_shed - feed_buffer
                    if excess > 0:
                        new_orders.append(["SELL", "WHEAT", excess])
                # If shed <= feed_buffer, order is completely suppressed (retained!)
        else:
            new_orders.append(order)

    # Force terminal liquidation of any leftover wheat on Step 696+ (Day 30)
    if step >= 696 and wheat_in_shed > 0:
        if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "WHEAT" for m in new_orders):
            new_orders.append(["SELL", "WHEAT", wheat_in_shed])

    act["market"] = new_orders
    return act

def run_wheat_proof(seed: int = 1000):
    print("=" * 125)
    print(f"EXP144 1-SEED PHYSICAL PROOF ON SEED {seed}")
    print("=" * 125)

    arms = [
        ("Arm A: Exact D.1 Control", agent_control),
        ("Arm B: Marginal Wheat Retention", agent_wheat_retention),
    ]

    for arm_name, ag_fn in arms:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        wheat_sold_early = 0
        wheat_sold_late = 0
        milk_harvested = 0
        d10_cash = 0.0
        d15_cash = 0.0
        d20_cash = 0.0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            farms = obs0.get("farms", [{}, {}])
            f0 = farms[0]

            if step == 240: d10_cash = float(f0.get("money", 0))
            elif step == 360: d15_cash = float(f0.get("money", 0))
            elif step == 480: d20_cash = float(f0.get("money", 0))

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)

            # Track wheat sales in market action
            if isinstance(a0, dict) and "market" in a0:
                for o in a0["market"]:
                    if len(o) >= 3 and o[0] == "SELL" and o[1] == "WHEAT":
                        if step < 600:
                            wheat_sold_early += o[2]
                        else:
                            wheat_sold_late += o[2]

            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        margin = r0 - r1
        won = (r0 > r1)

        print(f"  {arm_name:<35}: Reward=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${margin:+,.0f} | Won={won} | Wheat Early={wheat_sold_early} | Wheat Late={wheat_sold_late} | D10=${d10_cash:,.0f} | D15=${d15_cash:,.0f}")

if __name__ == "__main__":
    run_wheat_proof(seed=1000)
    run_wheat_proof(seed=42)
    run_wheat_proof(seed=20042)
