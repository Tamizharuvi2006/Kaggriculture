"""EXP154 Fast Worker: Fast Day-30 EV Sweep across Archetypes."""
from __future__ import annotations
import os
import sys
import json
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

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def create_day30_agent(n_hires: int):
    """Creates a D.1 agent that hires exactly n_hires workers at Step 696, then liquidates."""
    def agent_fn(obs, config=None):
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

            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])

            if step == 696 and n_hires > 0:
                hire_orders = [["HIRE"] for _ in range(n_hires)]
                merged = (hire_orders + clean_orders)[:10]
                act["market"] = merged
                return act

            if clean_orders:
                act["market"] = clean_orders[:10]
                return act

            return act

        return sub_d1.agent(obs, config)
    return agent_fn

def profile_and_sweep(seed: int, seat: int, b_key: str):
    opp_entry = POPULATION_SUITE[b_key]
    opp_fn = opp_entry["agent"]

    # 1. State at Step 696
    step696_state = {}
    sweep_rewards = {}

    for n in [0, 2, 4, 10]:
        agent_n = create_day30_agent(n)
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
            obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

            if step == 696 and n == 0:
                f0 = obs0.get("farms", [{}, {}])[0]
                tiles = f0.get("tiles", [])
                market = obs0.get("market", {})
                prices = market.get("prices", {})

                ripe_straw = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY" and t.get("age", 0) >= 3)
                ripe_wheat = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT" and t.get("age", 0) >= 1)
                cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
                curr_workers = len(f0.get("workers", []))
                money = float(f0.get("money", 0))

                p_straw = float(prices.get("STRAWBERRY", 120.0))
                p_milk = float(prices.get("MILK", 120.0))
                p_wheat = float(prices.get("WHEAT", 40.0))

                field_potential = (ripe_straw * p_straw) + (ripe_wheat * p_wheat) + (cows * p_milk * 0.5)

                step696_state = {
                    "money": money, "curr_workers": curr_workers,
                    "ripe_straw": ripe_straw, "ripe_wheat": ripe_wheat, "cows": cows,
                    "p_straw": p_straw, "p_milk": p_milk, "p_wheat": p_wheat,
                    "field_potential": field_potential,
                }

            a0 = agent_n(obs0, env.configuration)
            try: a1 = opp_fn(obs1, env.configuration)
            except TypeError: a1 = opp_fn(obs1)
            env.step([a0, a1] if seat == 0 else [a1, a0])

        r0 = float(env.state[seat].reward or 0.0)
        opp_r = float(env.state[1 - seat].reward or 0.0)
        sweep_rewards[f"N_{n}"] = {"reward": r0, "opp": opp_r, "margin": r0 - opp_r, "won": r0 > opp_r}

    best_n = max([0, 2, 4, 10], key=lambda n: sweep_rewards[f"N_{n}"]["reward"])
    best_reward = sweep_rewards[f"N_{best_n}"]["reward"]
    control_reward = sweep_rewards["N_0"]["reward"]

    return {
        "bot_key": b_key, "seed": seed, "seat": seat,
        "state_at_696": step696_state,
        "sweep_rewards": sweep_rewards,
        "best_n": best_n,
        "delta_best_vs_n0": best_reward - control_reward,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp154_fast_worker.py <bot_key_csv> <worker_id>")
        return

    bot_keys = sys.argv[1].split(",")
    worker_id = sys.argv[2]

    # Stratified 4 seeds per archetype (2 seat 0, 2 seat 1)
    seeds = [1000, 42, 20001, 20010]

    results = []
    for b_key in bot_keys:
        if b_key not in POPULATION_SUITE: continue
        for i, seed in enumerate(seeds):
            seat = 0 if i < 2 else 1
            res = profile_and_sweep(seed, seat, b_key)
            results.append(res)

    out_file = os.path.join(REPORTS_DIR, f"exp154_fast_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{worker_id}] completed {len(results)} matches -> {out_file}")

if __name__ == "__main__":
    main()
