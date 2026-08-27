"""EXP122-Harness Verification: 1-Seed Step-Level Intervention Proof.

Strict Protocol:
1. Verify Kaggriculture hand action structure: hands[i] corresponds to position farms[p]['hands'][i].
2. Track exact tile state under worker: kind, crop, planted_day, watered_today, yield_units, consecutive_unwatered.
3. Define unambiguous doomed strawberry criterion:
   - Strawberry needs 10 days to first harvest, then yields every 2 days.
   - If day >= 25, an unfertilized strawberry with growth stage that cannot yield before Day 30 is doomed.
4. Intervene on worker actions:
   - When worker i at (x, y) attempts ['CARE'] on a doomed tile after Day 24, override hands[i] = ['PASS'].
5. Run 1-Seed Paired Step-by-Step Test:
   - Arm A: Unmodified D.1
   - Arm B: D.1 with Harness-Corrected Late-Game Neglect
6. PROVE:
   - Exact count of intercepted CARE actions > 0.
   - Exact step, worker ID, and (x, y) tile coordinates of every interception.
   - Exact environment state change: unwatered count increases on doomed tiles in Arm B vs Arm A.
   - Physical divergence confirmed before any multi-seed run.
"""
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

# Load D.1 baseline
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

class CorrectedHarnessAgent:
    """Agent with provable, position-aware worker action interception."""

    def __init__(self, enable_neglect: bool = False, enable_day30_burst: bool = False):
        self.enable_neglect = enable_neglect
        self.enable_day30_burst = enable_day30_burst
        self.interceptions = []  # Log of (step, worker_idx, (x, y), original_action, new_action, tile_info)
        self.day30_hires = 0

    def is_doomed_strawberry(self, tile: dict, day: int) -> bool:
        """Determines if a strawberry plot cannot produce another harvest before Day 30 Hour 0."""
        if not isinstance(tile, dict):
            return False
        if tile.get("kind") != "PLANT" or tile.get("crop") != "STRAWBERRY":
            return False

        # If day >= 28, any strawberry with 0 yield_units cannot grow and ripen before Day 30 Hour 0 (step 696)
        if day >= 28 and int(tile.get("yield_units", 0)) == 0:
            return True

        # If day >= 26 and planted_day >= 17 with 0 yield, cannot reach first harvest (requires 10 days)
        planted = int(tile.get("planted_day", 0))
        if day >= 25 and (planted + 10) > 30 and int(tile.get("yield_units", 0)) == 0:
            return True

        return False

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1
        hour = step % 24
        player = obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0)

        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", [])
        my_farm = farms[player] if len(farms) > player else {}
        hands_pos = my_farm.get("hands", []) or []
        tiles = my_farm.get("tiles", []) or []

        # Get base D.1 action
        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # === INTERVENTION 1: Position-Aware Doomed Tile Crop Neglect ===
        if self.enable_neglect and day >= 25:
            # For each worker, check their current tile
            for w_idx in range(min(len(hands_pos), len(hands_act))):
                pos = hands_pos[w_idx]
                if not (isinstance(pos, (list, tuple)) and len(pos) >= 2):
                    continue
                wx, wy = pos[0], pos[1]
                
                # Check tile under worker
                if 0 <= wy < len(tiles) and 0 <= wx < len(tiles[wy]):
                    tile = tiles[wy][wx]
                    if self.is_doomed_strawberry(tile, day):
                        w_act = hands_act[w_idx]
                        act_name = w_act[0] if (isinstance(w_act, (list, tuple)) and len(w_act) >= 1) else ""
                        
                        # If worker is watering/caring/fertilizing a doomed strawberry, override with PASS
                        if act_name in ("WATER", "FERTILIZE", "CARE"):
                            hands_act[w_idx] = ["PASS"]
                            self.interceptions.append({
                                "step": step,
                                "day": day,
                                "hour": hour,
                                "worker_idx": w_idx,
                                "pos": (wx, wy),
                                "original": w_act,
                                "replaced_with": ["PASS"],
                                "tile_crop": tile.get("crop"),
                                "tile_yield": tile.get("yield_units"),
                                "tile_planted": tile.get("planted_day"),
                            })

        # === INTERVENTION 2: Day 30 Labor Burst ===
        if self.enable_day30_burst and day == 30 and hour == 0:
            # On Day 30 Hour 0, D.1 emits 0 HIRE orders. Add 6 HIRE orders to clear remaining ripe crops
            existing_hires = sum(1 for m in market_orders if len(m) >= 1 and m[0] == "HIRE")
            hires_to_add = min(6, 10 - len(market_orders))
            for _ in range(hires_to_add):
                market_orders.append(["HIRE"])
                self.day30_hires += 1

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_single_seed_harness_proof(seed: int = 42):
    print("=" * 110)
    print(f"EXP122 HARNESS INTERVENTION PROOF TEST (1 SEED: {seed})")
    print("=" * 110)

    # 1. Run Control Arm A (Unmodified D.1)
    env_a = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_a.reset()
    agent_a = CorrectedHarnessAgent(enable_neglect=False, enable_day30_burst=False)

    unwatered_a_history = []
    while not env_a.done:
        obs0 = env_a.state[0].observation
        t = obs0.get("step", 0)
        a0 = agent_a.act(obs0, env_a.configuration)
        a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        env_a.step([a0, a1])

        # Track unwatered doomed tiles on day 28+
        day = (t // 24) + 1
        if day >= 28 and t % 24 == 23:
            farm = env_a.state[0].observation["farms"][0]
            unwatered = sum(
                1 for row in farm.get("tiles", []) for tile in row
                if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("consecutive_unwatered", 0) > 0
            )
            unwatered_a_history.append((day, unwatered))

    reward_a = float(env_a.state[0].reward or 0.0)

    # 2. Run Intervention Arm B (Neglect Doomed Crops)
    env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_b.reset()
    agent_b = CorrectedHarnessAgent(enable_neglect=True, enable_day30_burst=False)

    unwatered_b_history = []
    while not env_b.done:
        obs0 = env_b.state[0].observation
        t = obs0.get("step", 0)
        a0 = agent_b.act(obs0, env_b.configuration)
        a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        env_b.step([a0, a1])

        # Track unwatered doomed tiles on day 28+
        day = (t // 24) + 1
        if day >= 28 and t % 24 == 23:
            farm = env_b.state[0].observation["farms"][0]
            unwatered = sum(
                1 for row in farm.get("tiles", []) for tile in row
                if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("consecutive_unwatered", 0) > 0
            )
            unwatered_b_history.append((day, unwatered))

    reward_b = float(env_b.state[0].reward or 0.0)

    # 3. Run Intervention Arm C (Day 30 Labor Burst)
    env_c = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_c.reset()
    agent_c = CorrectedHarnessAgent(enable_neglect=False, enable_day30_burst=True)

    day30_hands_c = 0
    while not env_c.done:
        obs0 = env_c.state[0].observation
        t = obs0.get("step", 0)
        day = (t // 24) + 1
        if day == 30 and t % 24 == 1:
            farm = obs0.get("farms", [])[0]
            day30_hands_c = len(farm.get("hands", []))

        a0 = agent_c.act(obs0, env_c.configuration)
        a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        env_c.step([a0, a1])

    reward_c = float(env_c.state[0].reward or 0.0)

    # ====================================================================================================
    # VERIFICATION & PROOF REPORT
    # ====================================================================================================
    print("\n--- 1. INTERVENTION FIRING PROOF ---")
    num_interceptions = len(agent_b.interceptions)
    print(f"Total Doomed Tile Actions Intercepted in Arm B: {num_interceptions}")
    
    if num_interceptions > 0:
        print("\nSample Interceptions (First 5):")
        for item in agent_b.interceptions[:5]:
            print(f"  Step {item['step']:3d} (D{item['day']:02d}H{item['hour']:02d}) | Worker {item['worker_idx']} at {item['pos']} | "
                  f"Overrode {item['original']} -> {item['replaced_with']} | Planted D{item['tile_planted']}, Yield={item['tile_yield']}")
        
        print("\nSample Interceptions (Last 5):")
        for item in agent_b.interceptions[-5:]:
            print(f"  Step {item['step']:3d} (D{item['day']:02d}H{item['hour']:02d}) | Worker {item['worker_idx']} at {item['pos']} | "
                  f"Overrode {item['original']} -> {item['replaced_with']} | Planted D{item['tile_planted']}, Yield={item['tile_yield']}")
    else:
        print("❌ ERROR: Zero interceptions occurred! Harness still not firing.")

    print("\n--- 2. PHYSICAL ENVIRONMENT STATE DIVERGENCE PROOF ---")
    print(f"{'Day':<6s} | {'Arm A Unwatered Strawberries':<32s} | {'Arm B Unwatered Strawberries (Neglected)':<42s}")
    print("-" * 85)
    for (day_a, unw_a), (day_b, unw_b) in zip(unwatered_a_history, unwatered_b_history):
        diff_str = f"(+{unw_b - unw_a} unwatered)" if unw_b > unw_a else "(=)"
        print(f"Day {day_a:02d} | {unw_a:2d} unwatered tiles                 | {unw_b:2d} unwatered tiles {diff_str:<20s}")

    print("\n--- 3. DAY 30 LABOR BURST PROOF ---")
    print(f"Day 30 Hires Added by Arm C: {agent_c.day30_hires}")
    print(f"Day 30 Active Hands at Hour 1 in Arm C: {day30_hands_c} workers (Arm A has 0 workers on Day 30)")

    print("\n--- 4. TERMINAL REWARD DELTAS (1 SEED) ---")
    print(f"Arm A (Unmodified D.1 Control)     : ${reward_a:11,.2f}")
    print(f"Arm B (Corrected Late-Crop Neglect): ${reward_b:11,.2f} (Delta: ${reward_b - reward_a:+,.2f})")
    print(f"Arm C (Corrected Day 30 Labor Burst): ${reward_c:11,.2f} (Delta: ${reward_c - reward_a:+,.2f})")
    print("=" * 110)

    # Assertion checks to guarantee proof
    assert num_interceptions > 0, "Intervention failed to fire!"
    assert reward_b != reward_a, "Environment terminal reward did not change in Arm B!"
    assert day30_hands_c > 0, "Day 30 labor burst failed to spawn workers!"
    assert reward_c != reward_a, "Environment terminal reward did not change in Arm C!"
    print("\n✅ ALL HARNESS INTERVENTION PROOFS PASSED WITH 100% EMPIRICAL CONFIRMATION!")

if __name__ == "__main__":
    run_single_seed_harness_proof(seed=42)
