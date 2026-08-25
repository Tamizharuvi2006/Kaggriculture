"""EXP039: Control Surface Discovery & Writable Knobs Audit.
Systematically tests candidate control surfaces of the APEX engine against the Reachability Gate
on Seed 42 to identify genuine, writable degrees of freedom vs inert pseudo-knobs.
"""
from __future__ import annotations
import sys
import os
import copy
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.evaluation.reachability_gate import verify_reachability, extract_farm_telemetry

def test_cs1_land_timing(day_target: int):
    """CS-1: Land Expansion Timing (SW on Day 8 vs Day 10)."""
    def _act(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        unlocked = set(own_farm.get("unlocked_quadrants", ["NW"]) or ["NW"])

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Writable Land Expansion Trigger
        if len(unlocked) == 2 and day >= day_target and "SW" not in unlocked and own_farm.get("money", 0) >= 2000.0:
            if not any(len(o) >= 1 and o[0] == "BUY_LAND" for o in orders):
                orders.append(["BUY_LAND"])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def test_cs2_plant_horizon(horizon_day: int):
    """CS-2: Strawberry Last Plant Horizon (Day 14 vs Day 18)."""
    def _act(obs, config=None):
        apex4_mod.DEFAULT_STRATEGY["strawberry_last_plant"] = horizon_day
        apex4_mod.STRATEGY["strawberry_last_plant"] = horizon_day
        return apex4_mod.agent(obs, config)
    return _act

def test_cs3_staffing_scale(workers: int):
    """CS-3: Staffing Ramp Scale (11 vs 12 vs 13 workers)."""
    def _act(obs, config=None):
        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        num_w = len(own_farm.get("hands", [])) + 1
        
        # Suppress HIRE if workers >= target
        if num_w >= workers:
            orders = [o for o in orders if not (isinstance(o, list) and len(o) >= 1 and o[0] == "HIRE")]
        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def test_cs4_batch_threshold(thresh: int):
    """CS-4: Liquidity Batch Threshold (qty >= 2 vs >= 4 vs >= 8)."""
    def _act(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Active Liquidity Injection
        for item in ("STRAWBERRY", "MILK", "WOOL"):
            qty = int(shed.get(item, 0) or 0)
            if qty >= thresh:
                if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                    if len(orders) < 10:
                        orders.append(["SELL", item, qty])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def test_cs5_endgame_timing(clearance_step: int):
    """CS-5: Endgame Clearance Timing (Step 672 vs Step 696 vs Step 710)."""
    def _act(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        if step >= clearance_step:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = int(shed.get(item, 0) or 0)
                if qty > 0:
                    if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                        if len(orders) < 10:
                            orders.append(["SELL", item, qty])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def test_cs6_opening_crop_mix(wheat: int, melons: int):
    """CS-6: Opening Crop Mix in DEFAULT_STRATEGY."""
    def _act(obs, config=None):
        apex4_mod.DEFAULT_STRATEGY["opening_wheat"] = wheat
        apex4_mod.DEFAULT_STRATEGY["opening_melons"] = melons
        apex4_mod.STRATEGY["opening_wheat"] = wheat
        apex4_mod.STRATEGY["opening_melons"] = melons
        return apex4_mod.agent(obs, config)
    return _act

def run_exp039():
    print("=" * 105)
    print("EXP039: APEX ENGINE CONTROL SURFACE DISCOVERY & WRITABLE KNOBS AUDIT")
    print("=" * 105)

    candidates = [
        ("CS-1: Land Expansion Timing (Day 8 Trigger)", test_cs1_land_timing(8)),
        ("CS-2: Planting Horizon Cap (Day 14 Cutoff)", test_cs2_plant_horizon(14)),
        ("CS-3: Staffing Scale Cap (11 Workers Cap)", test_cs3_staffing_scale(11)),
        ("CS-4: Liquidity Batch Threshold (qty >= 2)", test_cs4_batch_threshold(2)),
        ("CS-4: Liquidity Batch Threshold (qty >= 8)", test_cs4_batch_threshold(8)),
        ("CS-5: Endgame Clearance (Step 672 Early Clearance)", test_cs5_endgame_timing(672)),
        ("CS-5: Endgame Clearance (Step 710 Late Clearance)", test_cs5_endgame_timing(710)),
        ("CS-6: Opening Crop Mix (8 Wheat + 11 Melons)", test_cs6_opening_crop_mix(8, 11)),
    ]

    audit_table = []

    for name, agent_fn in candidates:
        passed, res = verify_reachability(agent_fn, name, seed=42)
        audit_table.append({
            "name": name,
            "writable": "YES [LIVE]" if passed else "NO [INERT]",
            "act_div": res["action_divergence_pct"],
            "mile_div": res["milestone_divergences"],
            "status": "VALID KNOB [OK]" if passed else "PSEUDO-KNOB [X]",
        })

    print("\n" + "=" * 105)
    print("EXP039 CONTROL SURFACE WRITABILITY & DEGREES OF FREEDOM REGISTRY")
    print("=" * 105)
    print(f"{'Control Surface Name':<45} | {'Writable?':<12} | {'Action Div %':>12} | {'Milestone Div':>14} | {'Status':<15}")
    print("-" * 105)

    for row in audit_table:
        print(f"{row['name']:<45} | {row['writable']:<12} | {row['act_div']:>11.1f}% | {row['mile_div']:>10} / 7 | {row['status']:<15}")

    print("=" * 105)

if __name__ == "__main__":
    run_exp039()
