"""EXP141 Multi-Opponent Worker: Evaluates Arms A, B, C, D across benchmark opponent suites."""
from __future__ import annotations
import os
import sys
import json
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_bot(bot_filename: str):
    p = os.path.join(BASE_DIR, "baseline", bot_filename)
    spec = importlib.util.spec_from_file_location("opp_bot", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def agent_control(obs, config=None):
    return sub_d1.agent(obs, config)

def make_care_agent(target_animal: str = "ALL"):
    def care_agent(obs, config=None):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = (step // 24) + 1
        act = sub_d1.agent(obs, config)

        if 6 <= day <= 10:
            player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
            farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
            own_f = farms[player] if len(farms) > player else {}
            pos = own_f.get("farmer", [0, 0])
            y, x = pos
            tiles = own_f.get("tiles", []) or []
            if y < len(tiles) and x < len(tiles[0]):
                t = tiles[y][x]
                if isinstance(t, dict) and "animal" in t:
                    an = t.get("animal")
                    cared = t.get("cared_today", False)
                    if not cared:
                        if target_animal == "ALL" or target_animal == an:
                            act["farmer"] = ["CARE"]
        return act
    return care_agent

def run_match(seed: int, seat: int, ag_fn, bot_mod):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = ag_fn(obs0, env.configuration)
        try:
            a1 = bot_mod.agent(obs1, env.configuration)
        except TypeError:
            a1 = bot_mod.agent(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])
    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return r0, r1, r0 > r1

def main():
    if len(sys.argv) < 3:
        print("Usage: python exp141_worker.py <bot_filename> <worker_id>")
        return

    bot_filename = sys.argv[1]
    worker_id = sys.argv[2]
    bot_mod = load_bot(bot_filename)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    ag_b = make_care_agent("COW")
    ag_c = make_care_agent("SHEEP")
    ag_d = make_care_agent("ALL")

    results = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1

        r_a, opp_a, won_a = run_match(seed, seat, agent_control, bot_mod)
        r_b, opp_b, won_b = run_match(seed, seat, ag_b, bot_mod)
        r_c, opp_c, won_c = run_match(seed, seat, ag_c, bot_mod)
        r_d, opp_d, won_d = run_match(seed, seat, ag_d, bot_mod)

        results.append({
            "opponent": bot_filename,
            "seed": seed,
            "seat": seat,
            "arm_a": {"reward": r_a, "opp": opp_a, "won": won_a},
            "arm_b": {"reward": r_b, "opp": opp_b, "won": won_b},
            "arm_c": {"reward": r_c, "opp": opp_c, "won": won_c},
            "arm_d": {"reward": r_d, "opp": opp_d, "won": won_d},
            "delta_b_vs_a": r_b - r_a,
            "delta_c_vs_a": r_c - r_a,
            "delta_d_vs_a": r_d - r_a,
        })

    out_file = os.path.join(REPORTS_DIR, f"exp141_part_{worker_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Worker [{bot_filename}:{worker_id}] complete -> {out_file}")

if __name__ == "__main__":
    main()
