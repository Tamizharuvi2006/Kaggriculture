"""EXP152 1-Seed Physical Proof: Inspecting Step 696 Market Payload & Labor Execution."""
from __future__ import annotations
import os
import sys
import copy
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def agent_arm_a(obs, config=None):
    """Arm A: Exact D.1 baseline (Control)."""
    return sub_d1.agent(obs, config)

def agent_arm_b_hire_first(obs, config=None):
    """Arm B: HIRE-Priority First (All valid HIREs first, remaining slots for clean_orders)."""
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    farms = obs.get("farms", [{}, {}]) if isinstance(obs, dict) else getattr(obs, "farms", [{}, {}])
    
    act = sub_d1._base_agent(obs)
    if not isinstance(act, dict):
        return act

    if step >= 696:
        own_farm = farms[0]
        shed = own_farm.get("inventory", {}) or {}
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)

        market_orders = list(act.get("market") or [])
        hires = [m for m in market_orders if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE"]
        
        clean_orders = []
        if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
        if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
        if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])

        # Priority 1: HIREs first, then clean_orders
        merged = hires + clean_orders
        act["market"] = merged[:10]
        return act

    return sub_d1.agent(obs, config)

def agent_arm_c_liq_first(obs, config=None):
    """Arm C: Liquidation-Priority First (clean_orders first, remaining slots for HIREs)."""
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    farms = obs.get("farms", [{}, {}]) if isinstance(obs, dict) else getattr(obs, "farms", [{}, {}])
    
    act = sub_d1._base_agent(obs)
    if not isinstance(act, dict):
        return act

    if step >= 696:
        own_farm = farms[0]
        shed = own_farm.get("inventory", {}) or {}
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)

        market_orders = list(act.get("market") or [])
        hires = [m for m in market_orders if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE"]
        
        clean_orders = []
        if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
        if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
        if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])

        # Priority 1: clean_orders first, then HIREs
        merged = clean_orders + hires
        act["market"] = merged[:10]
        return act

    return sub_d1.agent(obs, config)

def run_proof_match(seed: int, seat: int, hero_fn, arm_name: str):
    v18_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    step696_payload = []
    d30_workers_spawned = 0

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = hero_fn(obs0, env.configuration)
        try: a1 = v18_fn(obs1, env.configuration)
        except TypeError: a1 = v18_fn(obs1)

        if step == 696:
            step696_payload = list(a0.get("market", [])) if isinstance(a0, dict) else []

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    final_f0 = env.state[seat].observation.get("farms", [{}, {}])[seat]
    final_workers = len(final_f0.get("workers", []))

    print(f"  {arm_name:<30}: Reward=${r0:10,.2f} | Opp=${r1:10,.2f} | Margin=${r0 - r1:+10,.2f} | Won={r0 > r1} | EndWorkers={final_workers}")
    print(f"    Step 696 Market Orders ({len(step696_payload)} items): {step696_payload}")

def main():
    print("=" * 145)
    print("EXP152 1-SEED PHYSICAL PROOF ON SEED 1000 (V18 MIRROR)")
    print("=" * 145)
    run_proof_match(1000, 0, agent_arm_a, "Arm A: Control (Overwrites HIREs)")
    run_proof_match(1000, 0, agent_arm_b_hire_first, "Arm B: HIRE-Priority First")
    run_proof_match(1000, 0, agent_arm_c_liq_first, "Arm C: Liquidation-Priority First")
    print("=" * 145)

if __name__ == "__main__":
    main()
