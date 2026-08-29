"""EXP144 Multi-Opponent Worker: Evaluates Arm A (Control) vs Arm B (Marginal Wheat Retention)."""
from __future__ import annotations
import os
import sys
import json
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_bot(bot_filename: str):
    p = os.path.join(BASE_DIR, "baseline", bot_filename)
    spec = importlib.util.spec_from_file_location("opp_bot", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def agent_control(obs, config=None):
    return sub_d1.agent(obs, config)

def agent_wheat_retention(obs, config=None):
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

    remaining_days = max(0, 30 - day)
    downstream_val = (0.5 * p_milk) + p_fert if daily_feed_demand > 0 and remaining_days >= 2 else 0.0
    feed_buffer = daily_feed_demand * min(4, remaining_days)

    market_orders = list(act.get("market") or [])
    new_orders = []

    for order in market_orders:
        if isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL" and order[1] == "WHEAT":
            qty = int(order[2])
            if day >= 26 or downstream_val <= p_wheat or feed_buffer == 0:
                new_orders.append(order)
            else:
                if wheat_in_shed > feed_buffer:
                    excess = wheat_in_shed - feed_buffer
                    if excess > 0:
                        new_orders.append(["SELL", "WHEAT", excess])
        else:
            new_orders.append(order)

    if step >= 696 and wheat_in_shed > 0:
        if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "WHEAT" for m in new_orders):
            new_orders.append(["SELL", "WHEAT", wheat_in_shed])

    act["market"] = new_orders
    return act

def run_match(seed: int, seat: int, ag_fn, bot_mod):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = ag_fn(obs0, env.configuration)
        try:
            a1 = bot_mod.agent(obs1, env.configuration)
        except TypeError:
            a1 = bot_mod.agent(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])
    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return r0, r1, r0 > r1

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp144_worker.py <bot_filename> <worker_id>")
        return

    bot_filename = sys.argv[1]
    worker_id = sys.argv[2]
    bot_mod = load_bot(bot_filename)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    results = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1

        r_a, opp_a, won_a = run_match(seed, seat, agent_control, bot_mod)
        r_b, opp_b, won_b = run_match(seed, seat, agent_wheat_retention, bot_mod)

        results.append({
            "opponent": bot_filename,
            "seed": seed,
            "seat": seat,
            "arm_a": {"reward": r_a, "opp": opp_a, "won": won_a},
            "arm_b": {"reward": r_b, "opp": opp_b, "won": won_b},
            "delta_b_vs_a": r_b - r_a,
        })

    out_file = os.path.join(REPORTS_DIR, f"exp144_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{bot_filename}:{worker_id}] complete -> {out_file}")

if __name__ == "__main__":
    main()
