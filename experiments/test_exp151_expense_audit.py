"""EXP151 Balance Sheet & Expense Forensics: Itemizing every dollar of expenditure."""
from __future__ import annotations
import os
import sys
import importlib.util
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

def audit_match_expenses(seed: int, seat: int):
    v18_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    hero_exp = {"wages": 0.0, "seeds": 0.0, "animals": 0.0, "land": 0.0, "feed": 0.0, "fert": 0.0}
    opp_exp  = {"wages": 0.0, "seeds": 0.0, "animals": 0.0, "land": 0.0, "feed": 0.0, "fert": 0.0}

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = v18_fn(obs1, env.configuration)
        except TypeError: a1 = v18_fn(obs1)

        # In kaggriculture, check market buy orders
        m0 = a0.get("market", []) if isinstance(a0, dict) else []
        for o in m0:
            if isinstance(o, (list, tuple)) and len(o) >= 2:
                cmd = o[0]
                if cmd == "HIRE": hero_exp["wages"] += 500.0
                elif cmd == "BUY_LAND": hero_exp["land"] += (1000.0 if hero_exp["land"] == 0 else 2000.0)
                elif cmd == "BUY_SEED" and len(o) >= 3:
                    crop, qty = o[1], int(o[2])
                    cost_per = {"STRAWBERRY": 25.0, "CARROT": 5.0, "WHEAT": 5.0, "WATERMELON": 40.0, "MELON": 40.0}.get(crop, 20.0)
                    hero_exp["seeds"] += qty * cost_per
                elif cmd == "BUY_ANIMAL" and len(o) >= 3:
                    anim, qty = o[1], int(o[2])
                    cost_per = {"COW": 500.0, "SHEEP": 300.0}.get(anim, 500.0)
                    hero_exp["animals"] += qty * cost_per
                elif cmd == "BUY_FERTILIZER" and len(o) >= 3:
                    hero_exp["fert"] += int(o[2]) * 10.0

        m1 = a1.get("market", []) if isinstance(a1, dict) else []
        for o in m1:
            if isinstance(o, (list, tuple)) and len(o) >= 2:
                cmd = o[0]
                if cmd == "HIRE": opp_exp["wages"] += 500.0
                elif cmd == "BUY_LAND": opp_exp["land"] += (1000.0 if opp_exp["land"] == 0 else 2000.0)
                elif cmd == "BUY_SEED" and len(o) >= 3:
                    crop, qty = o[1], int(o[2])
                    cost_per = {"STRAWBERRY": 25.0, "CARROT": 5.0, "WHEAT": 5.0, "WATERMELON": 40.0, "MELON": 40.0}.get(crop, 20.0)
                    opp_exp["seeds"] += qty * cost_per
                elif cmd == "BUY_ANIMAL" and len(o) >= 3:
                    anim, qty = o[1], int(o[2])
                    cost_per = {"COW": 500.0, "SHEEP": 300.0}.get(anim, 500.0)
                    opp_exp["animals"] += qty * cost_per
                elif cmd == "BUY_FERTILIZER" and len(o) >= 3:
                    opp_exp["fert"] += int(o[2]) * 10.0

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "seed": seed, "seat": seat,
        "hero_reward": r0, "opp_reward": r1, "margin": r0 - r1,
        "hero_exp": hero_exp, "opp_exp": opp_exp,
    }

def main():
    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    all_audits = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1
        res = audit_match_expenses(seed, seat)
        all_audits.append(res)

    print("=" * 145)
    print("EXP151: FULL BALANCE SHEET EXPENSE AUDIT (D.1 HERO VS V18 OPPONENT)")
    print("=" * 145)
    print(f"{'Expense Category':<25} | {'D.1 Baseline Expense ($)':<28} | {'V18 Opponent Expense ($)':<28} | {'Delta Hero - Opp ($)'}")
    print("-" * 145)

    categories = ["wages", "seeds", "animals", "land", "fert"]
    tot_hero_exp, tot_opp_exp = 0.0, 0.0

    for cat in categories:
        h_val = np.mean([a["hero_exp"][cat] for a in all_audits])
        o_val = np.mean([a["opp_exp"][cat] for a in all_audits])
        tot_hero_exp += h_val
        tot_opp_exp += o_val
        print(f"{cat.capitalize():<25} | ${h_val:22,.2f}   | ${o_val:22,.2f}   | ${h_val - o_val:+22,.2f}")

    print("-" * 145)
    print(f"{'TOTAL CAPITAL EXPENDITURE':<25} | ${tot_hero_exp:22,.2f}   | ${tot_opp_exp:22,.2f}   | ${tot_hero_exp - tot_opp_exp:+22,.2f}")
    print("=" * 145)

if __name__ == "__main__":
    main()
