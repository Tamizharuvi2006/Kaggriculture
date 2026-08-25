"""EXP020: Forensic Loss Mining Lab.
Identifies and reconstructs the exact losses from the 64-game grand validation suite vs kaitofukami-v18.
Pinpoints the exact causal failure mode for every loss.
"""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent
from engine.evaluation.paired_replay import PairedEvaluator

def mine_losses():
    print("=" * 95)
    print("EXP020: FORENSIC LOSS MINING LAB (32 UNSEEN SEEDS x 2 SEATS = 64 MATCHES)")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    d1 = VariantDAgent()
    v18 = bot_v18.agent

    losses = []

    print("Screening for losses across all 64 matches...")
    for s in seeds:
        pair_res = PairedEvaluator.evaluate_pair(d1.act, v18, s, steps=720)
        
        # Check Match 1 (Candidate Seat 0 vs Opponent Seat 1)
        if pair_res["m1_win"] < 1.0:
            losses.append({
                "seed": s,
                "seat": 0,
                "cand_reward": pair_res["cand_seat0"],
                "opp_reward": pair_res["ctrl_seat1"],
                "delta": pair_res["cand_seat0"] - pair_res["ctrl_seat1"],
            })

        # Check Match 2 (Opponent Seat 0 vs Candidate Seat 1)
        if pair_res["m2_win"] < 1.0:
            losses.append({
                "seed": s,
                "seat": 1,
                "cand_reward": pair_res["cand_seat1"],
                "opp_reward": pair_res["ctrl_seat0"],
                "delta": pair_res["cand_seat1"] - pair_res["ctrl_seat0"],
            })

    print(f"\nFound {len(losses)} non-winning matches out of 64.")
    print("-" * 95)
    print(f"{'Index':<8} | {'Seed':>10} | {'Seat':>5} | {'Cand Money':>12} | {'Opp Money':>12} | {'Delta':>12}")
    print("-" * 95)
    for idx, l in enumerate(losses, 1):
        print(f"Match {idx:<3} | {l['seed']:10d} | {l['seat']:5d} | ${l['cand_reward']:11,.2f} | ${l['opp_reward']:11,.2f} | ${l['delta']:+11,.2f}")

    # Deep Trace Replay of the Worst Loss
    if losses:
        worst_loss = min(losses, key=lambda x: x["delta"])
        print("\n" + "=" * 95)
        print(f"DEEP FORENSIC TRACE: WORST MATCH (Seed {worst_loss['seed']}, Seat {worst_loss['seat']}, Delta ${worst_loss['delta']:+,.2f})")
        print("=" * 95)
        
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": worst_loss["seed"]})
        env.reset()
        
        c_agent = VariantDAgent()
        o_agent = bot_v18.agent
        
        agents = [c_agent.act, o_agent] if worst_loss["seat"] == 0 else [o_agent, c_agent.act]
        cand_idx = worst_loss["seat"]
        opp_idx = 1 - cand_idx

        step = 0
        milestones = [0, 71, 152, 170, 261, 360, 504, 600, 695, 719]
        
        print(f"{'Step':>5} | {'Day':>3} | {'Cand Money':>11} | {'Opp Money':>11} | {'Margin':>10} | {'Cand Shed':<25} | {'Opp Shed':<25}")
        print("-" * 105)

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            act0 = agents[0](obs0)
            act1 = agents[1](obs1)

            env.step([act0, act1])

            if step in milestones or env.done:
                f_cand = env.state[0].observation.farms[cand_idx]
                f_opp = env.state[0].observation.farms[opp_idx]
                
                m_cand = float(f_cand.get("money", 0))
                m_opp = float(f_opp.get("money", 0))
                
                shed_cand = env.state[cand_idx].observation.private.get("shed", {})
                shed_opp = env.state[opp_idx].observation.private.get("shed", {})

                cand_shed_str = str({k: v for k, v in shed_cand.items() if v > 0})[:24]
                opp_shed_str = str({k: v for k, v in shed_opp.items() if v > 0})[:24]

                print(f"{step:5d} | {step//24:3d} | ${m_cand:10,.0f} | ${m_opp:10,.0f} | ${m_cand - m_opp:+9,.0f} | {cand_shed_str:<25} | {opp_shed_str:<25}")

            step += 1

if __name__ == "__main__":
    mine_losses()
