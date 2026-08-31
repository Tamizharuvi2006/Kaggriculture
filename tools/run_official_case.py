"""Runs the official Kaggriculture Python engine and exports a normalized Checkpoint Trace JSON."""
import os
import sys
import json
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

CHECKPOINT_STEPS = [
    0, 72, 120, 144, 168, 216, 240, 264, 288, 312, 336, 360,
    480, 600, 672, 695, 696, 700, 705, 710, 715, 719, 720
]

def pass_agent(obs, conf=None):
    return {"farmer": ["PASS"], "hands": [], "market": []}

def starter_agent(obs, conf=None):
    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    private = obs.get("private", {}) or {}
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[player]
    fx, fy = farm["farmer"]
    tile = farm["tiles"][fy][fx]
    day = obs.get("day", 0)
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})

    market = []
    if shed.get("CARROT", 0) > 0:
        market.append(["SELL", "CARROT", shed["CARROT"]])
    if seeds.get("CARROT", 0) == 0 and farm["money"] >= 20:
        market.append(["BUY_SEED", "CARROT", 1])

    farmer = ["PASS"]
    if tile is None and seeds.get("CARROT", 0) > 0:
        farmer = ["PLANT", "CARROT"]
    elif isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == "CARROT":
        age = day - tile["planted_day"]
        if age >= 3:
            farmer = ["HARVEST"]
        elif not tile["watered_today"]:
            farmer = ["WATER"]
    return {"farmer": farmer, "hands": [], "market": market}

def resolve_policy(name):
    if name == "pass": return pass_agent
    if name == "starter": return starter_agent
    if name in ("v41", "v41_historical"):
        import generalization_pipeline.submission_candidate_competitive_hybrid_v4 as v41_mod
        return v41_mod.agent
    return pass_agent

def _call_agent(fn, obs, conf):
    if "step" not in obs:
        obs["step"] = obs.get("day", 0) * 24 + obs.get("hour", 0)
    try: return fn(obs, conf)
    except TypeError: return fn(obs)

def run_official_case(seed: int, seat: int, hero_name: str, opp_name: str, out_path: str = None) -> dict:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    hero_fn = resolve_policy(hero_name)
    opp_fn = resolve_policy(opp_name)

    env.info = {"seed": seed}
    env.configuration["seed"] = seed
    env.reset()

    trace = {
        "seed": seed,
        "hero_seat": seat,
        "hero_policy": hero_name,
        "opp_policy": opp_name,
        "final_rewards": [0.0, 0.0],
        "hero_won": False,
        "checkpoints": {}
    }

    opp_seat = 1 - seat
    checkpoints_set = set(CHECKPOINT_STEPS)

    def record_snap(step):
        o0, o1 = env.state[0].observation, env.state[1].observation
        o_hero = o0 if seat == 0 else o1
        o_opp = o0 if seat == 1 else o1

        f_hero = (o_hero.get("farms") or [{}, {}])[seat]
        f_opp = (o_opp.get("farms") or [{}, {}])[opp_seat]
        priv_hero = o_hero.get("private") or {}
        market = o_hero.get("market") or {}

        snap = {
            "step": step,
            "day": step // 24,
            "hour": step % 24,
            "hero_cash": float(f_hero.get("money", 0.0)),
            "opp_cash": float(f_opp.get("money", 0.0)),
            "market_prices": dict(market.get("prices") or {}),
            "market_inventory": dict(market.get("inventory") or {}),
            "hero_quads": len(f_hero.get("unlocked_quadrants") or ["NW"]),
            "opp_quads": len(f_opp.get("unlocked_quadrants") or ["NW"]),
            "hero_hands": len(f_hero.get("hands") or []),
            "opp_hands": len(f_opp.get("hands") or []),
            "hero_farmer_pos": list(f_hero.get("farmer") or [4, 4]),
            "opp_farmer_pos": list(f_opp.get("farmer") or [4, 4]),
            "hero_shed": dict(priv_hero.get("shed") or {}),
        }
        trace["checkpoints"][f"Step_{step}"] = snap

    while not env.done:
        step = env.state[0].observation.get("day", 0) * 24 + env.state[0].observation.get("hour", 0)
        if step in checkpoints_set:
            record_snap(step)

        o0, o1 = env.state[0].observation, env.state[1].observation
        o0["step"] = step
        o1["step"] = step
        if seat == 0:
            a0 = _call_agent(hero_fn, o0, env.configuration)
            a1 = _call_agent(opp_fn, o1, env.configuration)
        else:
            a0 = _call_agent(opp_fn, o0, env.configuration)
            a1 = _call_agent(hero_fn, o1, env.configuration)

        env.step([a0, a1])

    final_step = 720
    if 720 in checkpoints_set or f"Step_720" not in trace["checkpoints"]:
        record_snap(720)

    r0 = float(env.state[0].reward if env.state[0].reward is not None else env.state[0].observation.farms[0]["money"])
    r1 = float(env.state[1].reward if env.state[1].reward is not None else env.state[1].observation.farms[1]["money"])
    trace["final_rewards"] = [r0, r1]
    trace["hero_won"] = (r0 > r1) if seat == 0 else (r1 > r0)

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(trace, f, indent=2)
        print(f"Saved official trace to: {out_path}")

    return trace

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--seat", type=int, default=0)
    parser.add_argument("--hero", type=str, default="starter")
    parser.add_argument("--opponent", type=str, default="pass")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_official_case(args.seed, args.seat, args.hero, args.opponent, args.output)

if __name__ == "__main__":
    main()
