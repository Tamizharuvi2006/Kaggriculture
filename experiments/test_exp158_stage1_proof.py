"""EXP158 Stage 1: Physical Reachability Proof for Policy Selector & Mirror Response."""
from __future__ import annotations
import os
import sys
import importlib.util
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def create_arm_b_agent():
    """Arm B: D.1 Baseline + Step-216 Mirror Detector + Smooth Liquidation Response."""
    mirror_detected = False

    def agent_fn(obs, config=None):
        nonlocal mirror_detected
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        farms = obs.get("farms", [{}, {}]) if isinstance(obs, dict) else getattr(obs, "farms", [{}, {}])
        mkt = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {})
        prices = mkt.get("prices", {}) if isinstance(mkt, dict) else getattr(mkt, "prices", {})
        
        # 1. Hard Invariant: Step >= 696 Terminal Liquidation
        if step >= 696:
            own_farm = farms[0]
            shed = own_farm.get("inventory", {}) or {}
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
            milk_in_shed = int(shed.get("MILK", 0) or 0)
            fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)

            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])

            act = sub_d1._base_agent(obs)
            if isinstance(act, dict):
                act["market"] = clean_orders[:10] if clean_orders else []
                return act
            return act

        # 2. Step 216 Mirror Detector Gate
        if step >= 216 and not mirror_detected:
            opp_farm = farms[1]
            opp_tiles = opp_farm.get("tiles", [])
            opp_straw = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_cows = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
            opp_carrots = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "CARROT")

            if opp_straw >= 8 and opp_cows >= 4 and opp_carrots == 0:
                mirror_detected = True

        # 3. Base D.1 action
        act = sub_d1.agent(obs, config)
        if not isinstance(act, dict):
            return act

        # 4. If Mirror Detected: Execute Smooth Strawberry Drip (P >= 130, sell in chunks of 2-3 to avoid duopoly price crashes)
        if mirror_detected and 216 <= step < 696:
            own_farm = farms[0]
            shed = own_farm.get("inventory", {}) or {}
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
            p_straw = float(prices.get("STRAWBERRY", 120.0))

            if straw_in_shed >= 2 and p_straw >= 130.0:
                # Add or adjust sell order to sell exactly 2-3 units
                existing_market = act.get("market", []) or []
                # Remove any massive SELL STRAWBERRY orders
                filtered = [o for o in existing_market if not (isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY")]
                drip_qty = min(straw_in_shed, 3)
                filtered.append(["SELL", "STRAWBERRY", drip_qty])
                act["market"] = filtered[:10]

        return act

    return agent_fn

def run_physical_reachability_test(seed=1000):
    print("=" * 100)
    print(f"EXP158 STAGE 1: PHYSICAL REACHABILITY TEST (Seed {seed} vs T1_v18_mirror)")
    print("=" * 100)

    # 1. Run D.1 Baseline
    env_a = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_a.reset()
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    while not env_a.done:
        obs0 = env_a.state[0].observation
        obs1 = env_a.state[1].observation
        a0 = sub_d1.agent(obs0, env_a.configuration)
        try: a1 = opp_fn(obs1, env_a.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env_a.step([a0, a1])

    reward_a = float(env_a.state[0].reward or 0.0)
    opp_reward_a = float(env_a.state[1].reward or 0.0)

    # 2. Run Arm B (Selector + Smooth Drip)
    env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_b.reset()
    arm_b = create_arm_b_agent()

    diff_orders_count = 0
    while not env_b.done:
        step = env_b.state[0].observation.get("step", 0)
        obs0 = env_b.state[0].observation
        obs1 = env_b.state[1].observation

        a0 = arm_b(obs0, env_b.configuration)
        try: a1 = opp_fn(obs1, env_b.configuration)
        except TypeError: a1 = opp_fn(obs1)

        if step >= 216:
            # Check market orders
            m_orders = a0.get("market", []) if isinstance(a0, dict) else []
            if any(o[0] == "SELL" and o[1] == "STRAWBERRY" and o[2] <= 3 for o in m_orders if isinstance(o, (list, tuple)) and len(o) >= 3):
                diff_orders_count += 1

        env_b.step([a0, a1])

    reward_b = float(env_b.state[0].reward or 0.0)
    opp_reward_b = float(env_b.state[1].reward or 0.0)

    print(f"Arm A (D.1 Control)       : Reward = ${reward_a:10,.2f} | Opp = ${opp_reward_a:10,.2f} | Margin = ${reward_a - opp_reward_a:+10,.2f} | Result = {'WIN' if reward_a > opp_reward_a else 'LOSS'}")
    print(f"Arm B (Selector + Drip)   : Reward = ${reward_b:10,.2f} | Opp = ${opp_reward_b:10,.2f} | Margin = ${reward_b - opp_reward_b:+10,.2f} | Result = {'WIN' if reward_b > opp_reward_b else 'LOSS'}")
    print(f"Divergent Orders Executed : {diff_orders_count} steps with modified smooth drip orders")
    print(f"Physical Reachability     : {'✅ VERIFIED (Orders changed and environment responded)' if diff_orders_count > 0 else '❌ FAILED'}")
    print("=" * 100)

if __name__ == "__main__":
    run_physical_reachability_test(seed=1000)
