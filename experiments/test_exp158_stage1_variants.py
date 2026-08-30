"""EXP158 Stage 1: Multi-Variant Physical Reachability & Selection Gate."""
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

def create_variant_agent(mode: str):
    """
    mode='control': Standard D.1
    mode='peak_price_150': In mirror, gate strawberry sales strictly on P >= 150 (Day 10-29)
    mode='conservative_sell_140': In mirror, gate strawberry sales on P >= 140
    """
    mirror_detected = False

    def agent_fn(obs, config=None):
        nonlocal mirror_detected
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        farms = obs.get("farms", [{}, {}]) if isinstance(obs, dict) else getattr(obs, "farms", [{}, {}])
        mkt = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {})
        prices = mkt.get("prices", {}) if isinstance(mkt, dict) else getattr(mkt, "prices", {})
        
        # Hard Invariant: Step >= 696 Terminal Liquidation
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

        # Step 216 Mirror Detector
        if step >= 216 and not mirror_detected:
            opp_farm = farms[1]
            opp_tiles = opp_farm.get("tiles", [])
            opp_straw = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_cows = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
            opp_carrots = sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("crop") == "CARROT")

            if opp_straw >= 8 and opp_cows >= 4 and opp_carrots == 0:
                mirror_detected = True

        act = sub_d1.agent(obs, config)
        if not isinstance(act, dict):
            return act

        if mirror_detected and 216 <= step < 696:
            p_straw = float(prices.get("STRAWBERRY", 120.0))
            thresh = 150.0 if mode == "peak_price_150" else (140.0 if mode == "conservative_sell_140" else 0.0)
            if thresh > 0:
                existing_market = act.get("market", []) or []
                # If price is below threshold, defer STRAWBERRY sell orders
                if p_straw < thresh:
                    filtered = [o for o in existing_market if not (isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY")]
                    act["market"] = filtered

        return act

    return agent_fn

def test_variants_across_seeds():
    seeds = [1000, 42, 20001, 20010]
    variants = ["control", "conservative_sell_140", "peak_price_150"]
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    print("=" * 110)
    print("EXP158 STAGE 1: MIRROR RESPONSE SELECTION TEST (4 Seeds vs T1_v18_mirror)")
    print("=" * 110)

    results = {v: [] for v in variants}

    for v in variants:
        for seed in seeds:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            env.reset()
            agent = create_variant_agent(v)

            while not env.done:
                obs0 = env.state[0].observation
                obs1 = env.state[1].observation
                a0 = agent(obs0, env.configuration)
                try: a1 = opp_fn(obs1, env.configuration)
                except TypeError: a1 = opp_fn(obs1)
                env.step([a0, a1])

            r0 = float(env.state[0].reward or 0.0)
            r1 = float(env.state[1].reward or 0.0)
            results[v].append({"seed": seed, "hero": r0, "opp": r1, "margin": r0 - r1, "won": r0 > r1})

    print(f"{'Variant Mode':<26} | {'Mean Reward ($)':<16} | {'Opp Mean ($)':<16} | {'Mean Margin ($)':<16} | {'Win Rate'}")
    print("-" * 110)
    for v in variants:
        mean_r = np.mean([x["hero"] for x in results[v]])
        mean_opp = np.mean([x["opp"] for x in results[v]])
        mean_margin = np.mean([x["margin"] for x in results[v]])
        wins = sum(1 for x in results[v] if x["won"])
        print(f"{v:<26} | ${mean_r:12,.2f}   | ${mean_opp:12,.2f}   | ${mean_margin:+12,.2f}   | {wins}/{len(seeds)} ({wins/len(seeds)*100:.0f}%)")
    print("=" * 110)

if __name__ == "__main__":
    test_variants_across_seeds()
