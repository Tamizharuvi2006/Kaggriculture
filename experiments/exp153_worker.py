"""EXP153 Worker: Fast multi-process forensic mining of Steps 216 to 695 across V18 mirror matches."""
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

def analyze_match(seed: int, seat: int):
    v18_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    # Step-by-step logs for Steps 216 to 695
    divergences = []
    
    # Track cumulative actions
    h_seed_buys = {"STRAWBERRY": 0, "CARROT": 0, "WHEAT": 0, "WATERMELON": 0}
    o_seed_buys = {"STRAWBERRY": 0, "CARROT": 0, "WHEAT": 0, "WATERMELON": 0}
    
    h_plants_late = {"STRAWBERRY": 0, "CARROT": 0} # Day 26+ (step >= 624)
    o_plants_late = {"STRAWBERRY": 0, "CARROT": 0}

    h_feed_cows = 0
    o_feed_cows = 0

    h_market_sells = []
    o_market_sells = []

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = v18_fn(obs1, env.configuration)
        except TypeError: a1 = v18_fn(obs1)

        if 216 <= step <= 695:
            # 1. Market order audit
            m0 = a0.get("market", []) if isinstance(a0, dict) else []
            m1 = a1.get("market", []) if isinstance(a1, dict) else []

            for o in m0:
                if isinstance(o, (list, tuple)) and len(o) >= 3:
                    if o[0] == "BUY_SEED":
                        h_seed_buys[o[1]] = h_seed_buys.get(o[1], 0) + int(o[2])
                    elif o[0] == "SELL":
                        h_market_sells.append({"step": step, "item": o[1], "qty": int(o[2])})
            
            for o in m1:
                if isinstance(o, (list, tuple)) and len(o) >= 3:
                    if o[0] == "BUY_SEED":
                        o_seed_buys[o[1]] = o_seed_buys.get(o[1], 0) + int(o[2])
                    elif o[0] == "SELL":
                        o_market_sells.append({"step": step, "item": o[1], "qty": int(o[2])})

            # 2. Worker/Farmer action audit
            # Check late game plantings (Day 26+ / Step 624-695)
            if step >= 624:
                # Farmer action
                f0_act = a0.get("farmer", ["PASS"]) if isinstance(a0, dict) else ["PASS"]
                f1_act = a1.get("farmer", ["PASS"]) if isinstance(a1, dict) else ["PASS"]
                if len(f0_act) >= 2 and f0_act[0] == "PLANT":
                    h_plants_late[f0_act[1]] = h_plants_late.get(f0_act[1], 0) + 1
                if len(f1_act) >= 2 and f1_act[0] == "PLANT":
                    o_plants_late[f1_act[1]] = o_plants_late.get(f1_act[1], 0) + 1

                # Hands actions
                for h in a0.get("hands", []):
                    if isinstance(h, (list, tuple)) and len(h) >= 2 and h[0] == "PLANT":
                        h_plants_late[h[1]] = h_plants_late.get(h[1], 0) + 1
                for h in a1.get("hands", []):
                    if isinstance(h, (list, tuple)) and len(h) >= 2 and h[0] == "PLANT":
                        o_plants_late[h[1]] = o_plants_late.get(h[1], 0) + 1

            # 3. Feed cows audit
            for h in a0.get("hands", []):
                if isinstance(h, (list, tuple)) and len(h) >= 1 and h[0] == "FEED": h_feed_cows += 1
            for h in a1.get("hands", []):
                if isinstance(h, (list, tuple)) and len(h) >= 1 and h[0] == "FEED": o_feed_cows += 1

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "seed": seed, "seat": seat,
        "hero_reward": r0, "opp_reward": r1, "margin": r0 - r1, "won": r0 > r1,
        "h_seed_buys": h_seed_buys, "o_seed_buys": o_seed_buys,
        "h_plants_late": h_plants_late, "o_plants_late": o_plants_late,
        "h_feed_cows": h_feed_cows, "o_feed_cows": o_feed_cows,
        "h_sell_count": len(h_market_sells), "o_sell_count": len(o_market_sells),
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp153_worker.py <seed_list_csv> <worker_id>")
        return

    seeds = [int(s) for s in sys.argv[1].split(",") if s.strip()]
    worker_id = sys.argv[2]

    results = []
    for s in seeds:
        seat = 0 if s in [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321] else 1
        res = analyze_match(s, seat)
        results.append(res)

    out_file = os.path.join(REPORTS_DIR, f"exp153_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{worker_id}] complete -> {out_file}")

if __name__ == "__main__":
    main()
