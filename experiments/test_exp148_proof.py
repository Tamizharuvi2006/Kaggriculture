"""EXP148 1-Seed Physical Proof: Land #3 Causal Counterfactual & Strawberry Saturation."""
from __future__ import annotations
import os
import sys
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def agent_arm_a(obs, config=None):
    """Arm A: Exact D.1 Baseline Control."""
    return sub_d1.agent(obs, config)

def agent_arm_b(obs, config=None):
    """Arm B: Earliest Safe Land #3 Purchase."""
    act = sub_d1.agent(obs, config)
    if not isinstance(act, dict): return act

    player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
    farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
    own_f = farms[player] if len(farms) > player else {}
    money = float(own_f.get("money") or 0.0)
    unlocked = own_f.get("unlocked_quadrants") or [0]

    # If Land #2 is unlocked and Land #3 is locked, trigger BUY_LAND as soon as cash >= $2,200
    if len(unlocked) == 2 and money >= 2200.0:
        market = list(act.get("market") or [])
        if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market):
            market.append(["BUY_LAND"])
            act["market"] = market

    return act

def agent_arm_c(obs, config=None):
    """Arm C: D.1 + Immediate Strawberry Seed Purchase for Newly Unlocked Soil."""
    act = sub_d1.agent(obs, config)
    if not isinstance(act, dict): return act

    player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
    farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
    own_f = farms[player] if len(farms) > player else {}
    money = float(own_f.get("money") or 0.0)
    unlocked = own_f.get("unlocked_quadrants") or [0]
    tiles = own_f.get("tiles", [])
    shed = own_f.get("inventory") or {}
    straw_seeds = int(shed.get("STRAWBERRY_SEED", 0))

    # Check for empty arable soil tiles
    empty_soil_count = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") is None and t.get("animal") is None)

    if len(unlocked) >= 3 and empty_soil_count > straw_seeds and money >= 200.0:
        market = list(act.get("market") or [])
        needed_seeds = min(16, empty_soil_count - straw_seeds)
        if needed_seeds > 0 and not any(isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "BUY" and m[1] == "STRAWBERRY_SEED" for m in market):
            market.append(["BUY", "STRAWBERRY_SEED", needed_seeds])
            act["market"] = market

    return act

def agent_arm_d(obs, config=None):
    """Arm D: Earliest Safe Land #3 + Immediate Strawberry Saturation."""
    act = agent_arm_b(obs, config)
    return agent_arm_c(obs, config)

def run_proof_seed(seed: int = 1000):
    print("=" * 135)
    print(f"EXP148 1-SEED PHYSICAL PROOF ON SEED {seed}")
    print("=" * 135)

    arms = [
        ("Arm A: Exact D.1 Control", agent_arm_a),
        ("Arm B: Earliest Safe Land #3", agent_arm_b),
        ("Arm C: Strawberry Saturation", agent_arm_c),
        ("Arm D: Early Land #3 + Saturation", agent_arm_d),
    ]

    for arm_name, ag_fn in arms:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()

        quad3_unlock_step = None
        max_straw_tiles = 0
        d10_cash = 0.0
        d15_cash = 0.0

        while not env.done:
            step = env.state[0].observation.get("step", 0)
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            farms = obs0.get("farms", [{}, {}])
            f0 = farms[0]
            m0 = float(f0.get("money", 0))
            unlocked0 = f0.get("unlocked_quadrants") or [0]
            if len(unlocked0) >= 3 and quad3_unlock_step is None:
                quad3_unlock_step = step

            tiles0 = f0.get("tiles", [])
            straw_count = sum(1 for r in tiles0 for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if straw_count > max_straw_tiles:
                max_straw_tiles = straw_count

            if step == 240: d10_cash = m0
            elif step == 360: d15_cash = m0

            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)
            env.step([a0, a1])

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        margin = r0 - r1
        won = (r0 > r1)

        print(f"  {arm_name:<36}: Reward=${r0:,.0f} | Opp=${r1:,.0f} | Margin=${margin:+,.0f} | Won={won} | Land3Step={quad3_unlock_step} | MaxStrawTiles={max_straw_tiles} | D10=${d10_cash:,.0f} | D15=${d15_cash:,.0f}")

if __name__ == "__main__":
    run_proof_seed(seed=1000)
    run_proof_seed(seed=42)
    run_proof_seed(seed=20042)
