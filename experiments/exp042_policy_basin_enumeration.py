"""EXP042: Track B (True Policy-Space Basin Enumeration & Trajectory Clustering).
Evaluates candidate policy families against the Reachability Gate to identify genuinely distinct,
executable, and safe policy basins within the APEX engine.
"""
from __future__ import annotations
import sys
import os
import numpy as np

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

from engine.evaluation.reachability_gate import verify_reachability

# =============================================================================
# CANDIDATE POLICY FAMILY GENERATORS
# =============================================================================

def make_family_1_baseline():
    """Family 1: Baseline D.1 (Strawberry Titan Monolith)."""
    return apex4_mod.agent

def make_family_2_fast_turnover():
    """Family 2: Fast Turnover Sprint (Melon/Carrot Early Bridge)."""
    def _act(obs, config=None):
        apex4_mod.DEFAULT_STRATEGY["opening_melons"] = 14
        apex4_mod.DEFAULT_STRATEGY["opening_wheat"] = 6
        apex4_mod.STRATEGY["opening_melons"] = 14
        apex4_mod.STRATEGY["opening_wheat"] = 6
        return apex4_mod.agent(obs, config)
    return _act

def make_family_3_early_staffing():
    """Family 3: Aggressive Early Staffing (Rush 8 workers on Day 2)."""
    def _act(obs, config=None):
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        money = own_farm.get("money", 0)
        num_w = len(own_farm.get("hands", [])) + 1

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Aggressive early hiring
        if day <= 4 and num_w < 8 and money >= 200.0:
            if not any(len(o) >= 1 and o[0] == "HIRE" for o in orders):
                orders.append(["HIRE"])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def make_family_4_macro_batch():
    """Family 4: Extreme Macro-Batch Liquidity (qty >= 10)."""
    def _act(obs, config=None):
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        # Sell strictly in >= 10 unit mega batches
        for item in ("STRAWBERRY", "MILK", "WOOL"):
            qty = int(shed.get(item, 0) or 0)
            if qty >= 10:
                if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                    if len(orders) < 10:
                        orders.append(["SELL", item, qty])

        # Step 696 Clearance
        if step >= 696:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = int(shed.get(item, 0) or 0)
                if qty > 0:
                    if not any(len(o) >= 2 and o[0] == "SELL" and o[1] == item for o in orders):
                        if len(orders) < 10:
                            orders.append(["SELL", item, qty])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def make_family_5_late_replant():
    """Family 5: Extended Replanting Horizon (Cutoff Day 22 + Early SW Land on Day 8)."""
    def _act(obs, config=None):
        apex4_mod.DEFAULT_STRATEGY["strawberry_last_plant"] = 22
        apex4_mod.STRATEGY["strawberry_last_plant"] = 22
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        unlocked = set(own_farm.get("unlocked_quadrants", ["NW"]) or ["NW"])
        money = own_farm.get("money", 0)

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict): return base_act
        orders = list(base_act.get("market") or [])

        if len(unlocked) == 2 and day >= 8 and "SW" not in unlocked and money >= 2000.0:
            if not any(len(o) >= 1 and o[0] == "BUY_LAND" for o in orders):
                orders.append(["BUY_LAND"])

        return {"farmer": base_act.get("farmer"), "hands": base_act.get("hands"), "market": orders[:10]}
    return _act

def run_exp042():
    print("=" * 105)
    print("EXP042: TRUE POLICY-SPACE BASIN ENUMERATION & TRAJECTORY CLUSTERING")
    print("=" * 105)

    families = [
        ("Family 1: Baseline D.1 (Strawberry Titan)", make_family_1_baseline()),
        ("Family 2: Fast Turnover Sprint (Melon/Carrot Bridge)", make_family_2_fast_turnover()),
        ("Family 3: Aggressive Early Staffing (Day 2-4 Rush)", make_family_3_early_staffing()),
        ("Family 4: Extreme Macro-Batch (qty >= 10)", make_family_4_macro_batch()),
        ("Family 5: Extended Replant & Early SW Land", make_family_5_late_replant()),
    ]

    registry = []

    for name, agent_fn in families:
        passed, res = verify_reachability(agent_fn, name, seed=42)
        registry.append({
            "name": name,
            "action_div": res["action_divergence_pct"],
            "milestone_div": res["milestone_divergences"],
            "distinct": "YES [DISTINCT BASIN]" if (res["action_divergence_pct"] >= 5.0 or res["milestone_divergences"] > 0) else "NO [SAME BASIN]",
            "status": "VALIDATED BASIN" if passed else "COLLAPSED BASIN",
        })

    print("\n" + "=" * 105)
    print("EXP042 POLICY BASIN ENUMERATION REGISTRY")
    print("=" * 105)
    print(f"{'Policy Family Name':<48} | {'Action Div %':>12} | {'Milestone Div':>14} | {'Distinct Basin?':<18} | {'Status':<15}")
    print("-" * 105)

    for r in registry:
        print(f"{r['name']:<48} | {r['action_div']:>11.1f}% | {r['milestone_div']:>10} / 7 | {r['distinct']:<18} | {r['status']:<15}")

    print("=" * 105)

if __name__ == "__main__":
    run_exp042()
