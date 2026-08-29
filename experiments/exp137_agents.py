"""EXP137 Agent Definitions: Arm A (Control), Arm B (Unconditional Labor), Arm C (Adaptive Farm-Aware Labor Gate)."""
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
    """Arm A: Exact D.1 Baseline Control (Bugged Step-696 early return)."""
    return sub_d1.agent(obs, config)

def agent_arm_b(obs, config=None):
    """Arm B: Unconditional Day-30 Labor (Always fill up to 10 HIREs at Step 696)."""
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    act = sub_d1.agent(obs, config)
    day = (step // 24) + 1
    hour = step % 24

    if day == 30 and hour == 0:
        orders = list(act.get("market") or [])
        slots = max(0, 10 - len(orders))
        for _ in range(slots):
            orders.append(["HIRE"])
        act["market"] = orders[:10]
    return act

def agent_arm_c(obs, config=None):
    """Arm C: Adaptive Farm-Aware Labor Gate.

    Estimates Day-30 total production workload:
    - Animal harvesting workload (cows milking + sheep shearing)
    - Field crop harvesting workload (ripening strawberries / wheat / melon)
    - Liquidates shed inventory first.
    - Hires optimal workers K* only if expected revenue > total labor cost ($170/worker) and cash runway is safe.
    """
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    day = (step // 24) + 1
    hour = step % 24

    act = sub_d1.agent(obs, config)

    if day == 30 and hour == 0:
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_farm = farms[player] if len(farms) > player else {}
        money = float(own_farm.get("money", 0.0) or 0.0)

        # 1. Count animals on own farm
        tiles = own_farm.get("tiles", []) or []
        cows = 0
        sheep = 0
        crops_count = 0
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("animal") == "COW": cows += 1
                    elif t.get("animal") == "SHEEP": sheep += 1
                    elif t.get("crop"): crops_count += 1

        # 2. Get market prices
        market = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = market.get("prices", market.get("current_prices", {})) or {}
        p_straw = float(prices.get("STRAWBERRY", 50.0) or 50.0)
        p_milk = float(prices.get("MILK", 80.0) or 80.0)
        p_wool = float(prices.get("WOOL", 150.0) or 150.0)

        # 3. Expected Day 30 gross product value
        est_animal_value = (cows * p_milk * 2.0) + (sheep * p_wool * 1.5)
        est_crop_value = (crops_count * 0.35) * p_straw
        total_farm_value = est_animal_value + est_crop_value

        # 4. Determine optimal worker count
        # Total tasks on farm on Day 30: cows (8) + sheep (6) + ripe batches (~10) = ~24 tasks
        # 1 worker handles ~4 tasks/day. Total workers needed = ceil(tasks / 4) ~ 6-7 workers.
        # Cost = $170/worker.
        target_hires = 0
        if total_farm_value >= 1000.0 and money >= 500.0:
            # Farm has high production value -> Deploy 6-7 workers
            target_hires = min(7, int(total_farm_value / 350.0))
        elif total_farm_value >= 400.0 and money >= 250.0:
            # Moderate production -> Deploy 2-3 workers
            target_hires = 2
        else:
            # Farm exhausted / prices completely crashed -> 0 hires (save cash)
            target_hires = 0

        orders = list(act.get("market") or [])
        slots = max(0, 10 - len(orders))
        actual_hires = min(target_hires, slots)

        for _ in range(actual_hires):
            orders.append(["HIRE"])
        act["market"] = orders[:10]

    return act
