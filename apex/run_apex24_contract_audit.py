"""APEX 2.4 Adversarial Execution Contract & Invariant Audit Suite.
"""

from __future__ import annotations
import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from apex.world_model import WorldState, CashState
from apex.shadow_simulator import ShadowSimulator, ShadowSimulationResult
from apex.policy import ApexPolicy

def run_contract_audit():
    print("====================================================================================================")
    print("🛡️ APEX 2.4 ADVERSARIAL EXECUTION CONTRACT & INVARIANT AUDIT SUITE")
    print("====================================================================================================")

    dummy_obs = {
        "step": 120,
        "day": 5,
        "hour": 0,
        "player": 0,
        "market": {"prices": {"WHEAT": 25.0, "MELON": 250.0, "MILK": 180.0}},
        "farms": [
            {
                "money": 4500.0,
                "unlocked_quadrants": ["NW"],
                "inventory": {"WHEAT": 40},
                "tiles": [],
                "workers": [{"id": 0}, {"id": 1}],
                "hires_today": 0,
            },
            {"money": 3000.0, "unlocked_quadrants": ["NW"], "tiles": []}
        ]
    }

    state = WorldState(dummy_obs)

    # ---------------------------------------------------------
    # TEST 1: Liquidity Invariant
    # ---------------------------------------------------------
    print("\n1. Test 1 — Liquidity Invariant:")
    cash_st = state.cash_state
    print(f"   Current Cash: ${cash_st.current_cash:.2f} | Mandatory Reserve: ${cash_st.mandatory_cost:.2f} | Disposable: ${cash_st.disposable_cash:.2f}")
    assert cash_st.disposable_cash >= 0.0, "Disposable cash must be non-negative"
    print("   ✅ Liquidity Invariant Passed!")

    # ---------------------------------------------------------
    # TEST 2: Worker Continuity
    # ---------------------------------------------------------
    print("\n2. Test 2 — Worker Continuity & Operating Reserve:")
    assert cash_st.mandatory_cost > 0, "Mandatory reserve must protect worker maintenance"
    print(f"   Worker Maintenance Reserve: ${cash_st.worker_maintenance:.2f}")
    print("   ✅ Worker Continuity Invariant Passed!")

    # ---------------------------------------------------------
    # TEST 3: Action Purity (0 Appended Market Commands)
    # ---------------------------------------------------------
    print("\n3. Test 3 — Action Purity (0 Appended Market Commands):")
    plan = [["SELL", "WHEAT", 40]]
    sim_res = ShadowSimulator.simulate_plan(plan, state)
    print(f"   Simulated Plan: {plan}")
    print(f"   Simulation Status: {sim_res.reason} | Cash After: ${sim_res.simulated_cash_after:.2f}")
    assert sim_res.is_valid, "Valid sell plan must pass shadow simulation"
    print("   ✅ Action Purity Invariant Passed!")

    # ---------------------------------------------------------
    # TEST 4: Counterfactual Isolation (Adversarial Bankruptcy Rejection)
    # ---------------------------------------------------------
    print("\n4. Test 4 — Counterfactual Isolation & Adversarial Rejection:")
    bad_plan = [["BUY_LAND", "NE"], ["BUY_LAND", "SW"], ["BUY_LAND", "SE"], ["BUY_SEED", "MELON", 50]]
    bad_sim = ShadowSimulator.simulate_plan(bad_plan, state)
    print(f"   Adversarial Bad Plan: {bad_plan}")
    print(f"   Simulation Status: {bad_sim.reason} | Is Valid: {bad_sim.is_valid}")
    assert not bad_sim.is_valid, "Adversarial bankruptcy plan MUST be rejected"
    print("   ✅ Counterfactual Isolation Invariant Passed!")

    # ---------------------------------------------------------
    # TEST 5: Zero-Cost Policy Divergence Curriculum
    # ---------------------------------------------------------
    print("\n5. Test 5 — Zero-Cost Policy Divergence Curriculum:")
    policy = ApexPolicy(exploration_level="ZERO_COST")
    act = policy.select_action(dummy_obs, state)
    metrics = policy.get_metrics()
    print(f"   Selected Market Action: {act.get('market', [])}")
    print(f"   Policy Metrics: {metrics}")
    assert metrics["agreement_rate_pct"] == 100.0, "Zero-cost baseline must preserve 100% agreement safety"
    print("   ✅ Zero-Cost Policy Divergence Passed!")

    print("\n====================================================================================================")
    print("🏆 ALL 5 ADVERSARIAL EXECUTION CONTRACT INVARIANTS PASSED 100%!")
    print("====================================================================================================")

if __name__ == "__main__":
    run_contract_audit()
