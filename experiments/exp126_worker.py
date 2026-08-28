"""EXP126 Chunk Worker: Evaluates 4 Arms (A, B, C, D) on a slice of the 100 loss matches."""
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

class EXP126Agent:
    def __init__(self, midgame_accel: bool = False, day30_burst: bool = False, min_trapped: int = 16, accel_hires: int = 2, day30_hires: int = 6):
        self.midgame_accel = midgame_accel
        self.day30_burst = day30_burst
        self.min_trapped = min_trapped
        self.accel_hires = accel_hires
        self.day30_hires = day30_hires
        self.trigger_count = 0
        self.earliest_trigger_step = None
        self.total_extra_hires = 0

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Check Midgame Trigger (Days 20-26 Hour 0)
        if self.midgame_accel and 20 <= day <= 26 and hour == 0:
            player = int(obs.get("player", 0) or 0)
            farms = obs.get("farms", [])
            farm = farms[player] if len(farms) > player and isinstance(farms[player], dict) else {}
            trapped = sum(
                tile.get("yield_units", 0)
                for row in (farm.get("tiles") or [])
                for tile in (row if isinstance(row, list) else [row])
                if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY"
            )
            money = float(farm.get("money", 0.0) or 0.0)
            if trapped >= self.min_trapped and money >= 2000.0:
                slots = max(0, 10 - len(market_orders))
                to_add = min(self.accel_hires, slots)
                for _ in range(to_add):
                    market_orders.append(["HIRE"])
                    self.total_extra_hires += 1
                self.trigger_count += 1
                if self.earliest_trigger_step is None:
                    self.earliest_trigger_step = step

        # Check Day 30 Burst Trigger (Day 30 Hour 0)
        if self.day30_burst and day == 30 and hour == 0:
            slots = max(0, 10 - len(market_orders))
            to_add = min(self.day30_hires, slots)
            for _ in range(to_add):
                market_orders.append(["HIRE"])
                self.total_extra_hires += 1
            if self.earliest_trigger_step is None:
                self.earliest_trigger_step = step

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_single_match(agent_d1_obj, seed: int, d1_seat: int):
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
            a_opp = bot_v18_mod.agent(opp_obs, env.configuration)
        except TypeError:
            a_opp = bot_v18_mod.agent(opp_obs) if hasattr(bot_v18_mod, "agent") else bot_v18_mod(opp_obs)

        a0 = a_d1 if seat_0_is_d1 else a_opp
        a1 = a_opp if seat_0_is_d1 else a_d1
        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    d1_rew = r0 if seat_0_is_d1 else r1
    opp_rew = r1 if seat_0_is_d1 else r0
    won = d1_rew > opp_rew
    delta = d1_rew - opp_rew

    # Count stranded crops
    final_obs = env.state[d1_seat].observation
    farms = final_obs.get("farms", [])
    d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
    stranded = 0
    for row in (d1_farm.get("tiles") or []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("kind") == "PLANT":
                if tile.get("yield_units", 0) > 0:
                    stranded += tile.get("yield_units", 0)

    return {
        "reward": d1_rew,
        "opp_reward": opp_rew,
        "won": won,
        "delta": delta,
        "stranded": stranded,
        "trigger_count": agent_d1_obj.trigger_count,
        "earliest_step": agent_d1_obj.earliest_trigger_step,
        "extra_hires": agent_d1_obj.total_extra_hires,
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp126_worker.py <start_idx> <end_idx>")
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

        # Arm A: Control D.1
        agent_a = EXP126Agent()
        res_a = run_single_match(agent_a, seed=seed, d1_seat=seat)

        # Arm B: Midgame Accelerator Only
        agent_b = EXP126Agent(midgame_accel=True)
        res_b = run_single_match(agent_b, seed=seed, d1_seat=seat)

        # Arm C: Day 30 Labor Burst Only
        agent_c = EXP126Agent(day30_burst=True)
        res_c = run_single_match(agent_c, seed=seed, d1_seat=seat)

        # Arm D: Combined (Arm B + Arm C)
        agent_d = EXP126Agent(midgame_accel=True, day30_burst=True)
        res_d = run_single_match(agent_d, seed=seed, d1_seat=seat)

        results.append({
            "match_id": i,
            "seed": seed,
            "seat": seat,
            "arm_a": res_a,
            "arm_b": res_b,
            "arm_c": res_c,
            "arm_d": res_d,
        })

    out_part = os.path.join(REPORTS_DIR, f"exp126_part_{start_idx}_{end_idx}.json")
    with open(out_part, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{start_idx}:{end_idx}] completed -> {out_part}")

if __name__ == "__main__":
    main()
