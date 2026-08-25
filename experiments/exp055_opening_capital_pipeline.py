"""EXP055: Track B (Opening Capital Pipeline & Bottleneck Physics Audit).
High-resolution step-by-step trace of the Days 0-6 (Steps 0-144) initial capital formation pipeline:
Measures:
1. t_plant: Exact step initial opening seeds are planted (Wheat/Melon).
2. t_ripe: Exact step opening crops reach fully ripe stage.
3. t_harvest_deposit: Exact step ripe crops are harvested and deposited into shed.
4. t_first_sell: Exact step market SELL order is executed.
5. t_first_straw_capital: Exact step bank reaches >= $950 (Land #2 + Strawberry Seed capital).
6. Latency Analysis:
   - Harvest Lag = t_harvest_deposit - t_ripe
   - Liquidity Submission Lag = t_first_sell - t_harvest_deposit
   - Reinvestment Lag = t_first_straw_capital - t_first_sell
Determines whether the opening capital pipeline is mathematically locked at the physical limit.
"""
from __future__ import annotations
import sys
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

def trace_seed_capital_pipeline(seed: int) -> list[dict]:
    """Traces the step-level opening cash timeline on a single seed across both seats."""
    results = []

    for seat in [0, 1]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        agent_d1 = VariantDAgent()

        step = 0
        t_plant = None
        t_ripe = None
        t_harvest_deposit = None
        t_first_sell = None
        t_first_straw_capital = None

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            if seat == 0:
                act = agent_d1.act(obs0, env.configuration)
                opp_act = bot_v18.agent(obs1)
                own_obs = obs0
            else:
                opp_act = bot_v18.agent(obs0)
                act = agent_d1.act(obs1, env.configuration)
                own_obs = obs1

            farms = own_obs.get("farms") or []
            own_farm = farms[seat] if len(farms) > seat else {}
            money = float(own_farm.get("money", 0))
            tiles = own_farm.get("tiles") or []
            priv = own_obs.get("private") or {}
            shed = priv.get("shed") or {}

            # 1. Detect t_plant
            if t_plant is None:
                has_planted = any(isinstance(tile, dict) and tile.get("crop") is not None for row in tiles for tile in row)
                if has_planted:
                    t_plant = step

            # 2. Detect t_ripe (stage >= 3 on any crop)
            if t_ripe is None:
                has_ripe = any(isinstance(tile, dict) and tile.get("crop") is not None and tile.get("stage", 0) >= 3 for row in tiles for tile in row)
                if has_ripe:
                    t_ripe = step

            # 3. Detect t_harvest_deposit (shed has harvested crops)
            if t_harvest_deposit is None:
                shed_crops = sum(int(shed.get(c, 0) or 0) for c in ("WHEAT", "MELON", "CARROT", "TOMATO", "STRAWBERRY"))
                if shed_crops > 0:
                    t_harvest_deposit = step

            # 4. Detect t_first_sell (market order has SELL command)
            if t_first_sell is None and isinstance(act, dict):
                orders = act.get("market") or []
                if any(len(o) >= 2 and o[0] == "SELL" for o in orders):
                    t_first_sell = step

            # 5. Detect t_first_straw_capital (money >= $950)
            if t_first_straw_capital is None and money >= 950.0:
                t_first_straw_capital = step

            env.step([act, opp_act] if seat == 0 else [opp_act, act])
            step += 1

        final_bank = float(env.state[seat].reward or 0.0)
        opp_bank = float(env.state[1 - seat].reward or 0.0)

        results.append({
            "seed": seed,
            "seat": seat,
            "d1_bank": final_bank,
            "opp_bank": opp_bank,
            "is_win": final_bank > opp_bank,
            "t_plant": t_plant or 0,
            "t_ripe": t_ripe or 0,
            "t_harvest_deposit": t_harvest_deposit or 0,
            "t_first_sell": t_first_sell or 0,
            "t_first_straw_capital": t_first_straw_capital or 0,
        })

    return results

def run_exp055():
    print("=" * 105)
    print("EXP055: OPENING CAPITAL PIPELINE & BOTTLENECK PHYSICS AUDIT (64 MATCHES / 32 SEEDS)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel step-level cash pipeline tracing across 64 matches...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(trace_seed_capital_pipeline, seeds))

    all_traces = [t for sub in nested_res for t in sub]

    t_plants = [t["t_plant"] for t in all_traces]
    t_ripes = [t["t_ripe"] for t in all_traces]
    t_harvests = [t["t_harvest_deposit"] for t in all_traces]
    t_sells = [t["t_first_sell"] for t in all_traces]
    t_capitals = [t["t_first_straw_capital"] for t in all_traces]

    harvest_lags = [t["t_harvest_deposit"] - t["t_ripe"] for t in all_traces]
    sell_lags = [t["t_first_sell"] - t["t_harvest_deposit"] for t in all_traces]

    print("\n" + "=" * 105)
    print("1. OPENING CAPITAL PIPELINE MILESTONE TIMELINE (Average Steps & Days across 64 Matches)")
    print("=" * 105)
    print(f"{'Pipeline Event / Milestone':<38} | {'Mean Step':>12} | {'Day Equivalent':>16} | {'Physical Engine Meaning'}")
    print("-" * 105)
    print(f"{'t_plant (Initial Seeds Planted)':<38} | {np.mean(t_plants):>12.1f} | Day {np.mean(t_plants)/24:>12.2f} | Initial Wheat/Melon plot seeding")
    print(f"{'t_ripe (Opening Crop Ripens)':<38} | {np.mean(t_ripes):>12.1f} | Day {np.mean(t_ripes)/24:>12.2f} | 3-day growth cycle completes")
    print(f"{'t_harvest_deposit (Harvested in Shed)':<38} | {np.mean(t_harvests):>12.1f} | Day {np.mean(t_harvests)/24:>12.2f} | Worker harvests and drops in shed")
    print(f"{'t_first_sell (Market SELL Executed)':<38} | {np.mean(t_sells):>12.1f} | Day {np.mean(t_sells)/24:>12.2f} | Town shop purchase fills order")
    print(f"{'t_first_straw_capital (Bank >= $950)':<38} | {np.mean(t_capitals):>12.1f} | Day {np.mean(t_capitals)/24:>12.2f} | Capital reaches Land #2 + Strawberry funds")
    print("=" * 105)

    print("\n" + "=" * 105)
    print("2. PIPELINE FRICTION & LATENCY ANALYSIS")
    print("=" * 105)
    print(f"  - Harvest Latency (t_harvest - t_ripe)      : Mean = {np.mean(harvest_lags):.1f} steps (Median = {np.median(harvest_lags):.0f} steps)")
    print(f"  - Liquidity Submission Lag (t_sell - t_shed) : Mean = {np.mean(sell_lags):.1f} steps (Median = {np.median(sell_lags):.0f} steps)")
    print(f"  - Total Capital Formation Time (t_capital)   : Mean = {np.mean(t_capitals):.1f} steps (Day {np.mean(t_capitals)/24:.1f})")
    print("=" * 105)

    # Mathematical Proof
    print("\n3. FORENSIC CAPACITY VERDICT:")
    if np.mean(harvest_lags) <= 1.0 and np.mean(sell_lags) <= 1.0:
        print("  >>> VERDICT: OPENING CAPITAL PIPELINE OPERATES AT ZERO-LAG THEORETICAL MAXIMUM.")
        print("      Crops are harvested the instant they ripen, deposited, and sold on the same step.")
        print("      t_capital is bound strictly by the 3-day physical biological crop growth cycle (72 steps).")
        print("      Opening capital acceleration is physically locked at the theoretical minimum.")
    else:
        print(f"  >>> VERDICT: ACTIONABLE LATENCY DETECTED: {np.mean(harvest_lags)+np.mean(sell_lags):.1f} steps of potential acceleration available.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp055()
