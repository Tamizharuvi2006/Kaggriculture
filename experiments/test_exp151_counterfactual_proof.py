"""EXP151 Counterfactual Proof: Day 30 Labor Preservation under MIRROR_MODE."""
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
    """Control: Exact D.1 baseline."""
    return sub_d1.agent(obs, config)

def agent_arm_b_mirror_fix(obs, config=None):
    """Arm B: EXP150 Detector + Day 30 Labor Order Preservation."""
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    farms = obs.get("farms", [{}, {}]) if isinstance(obs, dict) else getattr(obs, "farms", [{}, {}])
    
    # We call the clean logic but preserve HIRE orders on Day 30 clearance
    act = sub_d1._base_agent(obs)
    if not isinstance(act, dict):
        return act

    # Run the outer wrapper logic with HIRE preservation
    own_farm = farms[0]
    shed = own_farm.get("inventory", {}) or {}
    straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
    milk_in_shed = int(shed.get("MILK", 0) or 0)
    fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)

    market_orders = list(act.get("market") or [])

    if step >= 696:
        # Preserve HIRE orders from base agent, and append clearance sales!
        hires = [m for m in market_orders if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE"]
        clean_orders = []
        if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
        if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
        if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])
        
        # Merge hires and clean orders up to 10 total
        merged = hires + clean_orders
        act["market"] = merged[:10]
        return act

    return sub_d1.agent(obs, config)

def main():
    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    v18_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    print("=" * 145)
    print("EXP151: COUNTERFACTUAL PROOF (ARM A CONTROL VS ARM B DAY 30 LABOR PRESERVATION) ON 20 MIRROR MATCHES")
    print("=" * 145)
    print(f"{'Seed':<10} | {'Seat':<6} | {'Arm A Reward':<16} | {'Arm B Reward':<16} | {'Opponent Reward':<18} | {'Delta B vs A ($)':<18} | {'Arm A Won':<10} | {'Arm B Won'}")
    print("-" * 145)

    a_wins, b_wins = 0, 0
    tot_a_rew, tot_b_rew, tot_opp_rew = 0.0, 0.0, 0.0

    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1

        # Match Arm A
        env_a = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_a.reset()
        while not env_a.done:
            obs0 = env_a.state[0].observation if seat == 0 else env_a.state[1].observation
            obs1 = env_a.state[1].observation if seat == 0 else env_a.state[0].observation
            a0 = agent_arm_a(obs0, env_a.configuration)
            try: a1 = v18_fn(obs1, env_a.configuration)
            except TypeError: a1 = v18_fn(obs1)
            env_a.step([a0, a1] if seat == 0 else [a1, a0])
        r_a = float(env_a.state[seat].reward or 0.0)
        opp_a = float(env_a.state[1 - seat].reward or 0.0)
        won_a = r_a > opp_a

        # Match Arm B
        env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_b.reset()
        while not env_b.done:
            obs0 = env_b.state[0].observation if seat == 0 else env_b.state[1].observation
            obs1 = env_b.state[1].observation if seat == 0 else env_b.state[0].observation
            a0 = agent_arm_b_mirror_fix(obs0, env_b.configuration)
            try: a1 = v18_fn(obs1, env_b.configuration)
            except TypeError: a1 = v18_fn(obs1)
            env_b.step([a0, a1] if seat == 0 else [a1, a0])
        r_b = float(env_b.state[seat].reward or 0.0)
        opp_b = float(env_b.state[1 - seat].reward or 0.0)
        won_b = r_b > opp_b

        if won_a: a_wins += 1
        if won_b: b_wins += 1
        tot_a_rew += r_a
        tot_b_rew += r_b
        tot_opp_rew += opp_b

        print(f"{seed:<10} | {seat:<6} | ${r_a:12,.2f}   | ${r_b:12,.2f}   | ${opp_b:12,.2f}     | ${r_b - r_a:+14,.2f}   | {str(won_a):<10} | {str(won_b)}")

    print("-" * 145)
    print(f"{'OVERALL':<10} | {'ALL':<6} | ${tot_a_rew/len(seeds):12,.2f}   | ${tot_b_rew/len(seeds):12,.2f}   | ${tot_opp_rew/len(seeds):12,.2f}     | ${(tot_b_rew - tot_a_rew)/len(seeds):+14,.2f}   | {a_wins}/{len(seeds)} ({(a_wins/len(seeds))*100:.1f}%) | {b_wins}/{len(seeds)} ({(b_wins/len(seeds))*100:.1f}%)")
    print("=" * 145)

if __name__ == "__main__":
    main()
