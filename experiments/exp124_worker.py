"""EXP124 Chunk Worker: Runs a slice of the 100 frozen loss matches."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

class Day30LaborBurstAgent:
    def __init__(self, enable_burst: bool = False, max_hires: int = 6):
        self.enable_burst = enable_burst
        self.max_hires = max_hires

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        if self.enable_burst and day == 30 and hour == 0:
            slots_available = max(0, 10 - len(market_orders))
            hires_to_add = min(self.max_hires, slots_available)
            for _ in range(hires_to_add):
                market_orders.append(["HIRE"])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_single_match(agent_d1_obj, bot_opp, seed: int, d1_seat: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    seat_0_is_d1 = (d1_seat == 0)

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        d1_obs = obs0 if seat_0_is_d1 else obs1
        a_d1 = agent_d1_obj.act(d1_obs, env.configuration)

        opp_obs = obs1 if seat_0_is_d1 else obs0
        try:
            a_opp = bot_opp.agent(opp_obs, env.configuration)
        except TypeError:
            a_opp = bot_opp.agent(opp_obs) if hasattr(bot_opp, "agent") else bot_opp(opp_obs)

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    d1_rew = r0 if seat_0_is_d1 else r1
    opp_rew = r1 if seat_0_is_d1 else r0
    won = d1_rew > opp_rew
    delta = d1_rew - opp_rew

    final_obs = env.state[d1_seat].observation
    farms = final_obs.get("farms", [])
    d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
    stranded = 0
    for row in (d1_farm.get("tiles") or []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("kind") == "PLANT":
                if tile.get("yield_units", 0) > 0:
                    stranded += 1

    return {
        "reward": d1_rew,
        "opp_reward": opp_rew,
        "won": won,
        "delta": delta,
        "stranded": stranded,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp124_worker.py <start_idx> <end_idx>")
        return

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    chunk = loss_cohort[start_idx:end_idx]
    results = []

    for i, match_info in enumerate(chunk, start=start_idx + 1):
        seed = match_info["seed"]
        seat = match_info["seat"]

        agent_a = Day30LaborBurstAgent(enable_burst=False)
        res_a = run_single_match(agent_a, bot_v18_mod, seed=seed, d1_seat=seat)

        agent_b = Day30LaborBurstAgent(enable_burst=True, max_hires=6)
        res_b = run_single_match(agent_b, bot_v18_mod, seed=seed, d1_seat=seat)

        reward_delta = res_b["reward"] - res_a["reward"]

        if not res_a["won"] and res_b["won"]:
            transition = "LOSS_TO_WIN"
        elif not res_a["won"] and not res_b["won"]:
            transition = "LOSS_TO_LOSS"
        elif res_a["won"] and not res_b["won"]:
            transition = "WIN_TO_LOSS"
        else:
            transition = "WIN_TO_WIN"

        results.append({
            "match_id": i,
            "seed": seed,
            "seat": seat,
            "arm_a_reward": res_a["reward"],
            "arm_a_opp_reward": res_a["opp_reward"],
            "arm_a_won": res_a["won"],
            "arm_a_stranded": res_a["stranded"],
            "arm_b_reward": res_b["reward"],
            "arm_b_opp_reward": res_b["opp_reward"],
            "arm_b_won": res_b["won"],
            "arm_b_stranded": res_b["stranded"],
            "reward_delta": reward_delta,
            "transition": transition,
            "stranded_reduced": res_a["stranded"] - res_b["stranded"],
        })

    out_part = os.path.join(REPORTS_DIR, f"exp124_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Completed chunk [{start_idx}:{end_idx}] -> {out_part}")

if __name__ == "__main__":
    main()
