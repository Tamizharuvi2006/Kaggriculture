"""Probe comparing Arm A (Control) vs Arm B1 (Blind 10 HIRE) vs Arm B2 (Liquidation + HIRE Fill)."""
import os
import sys
import kaggle_environments
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def agent_b2(obs, config=None):
    """Arm B2: Liquidation sells first, then fill remaining slots with HIREs from core schedule."""
    step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
    act = sub_d1.agent(obs, config)
    day = (step // 24) + 1
    hour = step % 24

    if day == 30 and hour == 0:
        orders = list(act.get("market") or [])
        slots = max(0, 10 - len(orders))
        for _ in range(slots):
            orders.append(["HIRE"])
        act["market"] = orders[:10]
    return act

def test_seed(seed: int):
    print(f"\n--- Seed {seed} ---")
    for name, ag_fn in [("Control A (0 HIRE, All Sells)", sub_d1.agent), ("Arm B2 (Sells First + HIRE Fill)", agent_b2)]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation
            a0 = ag_fn(obs0, env.configuration)
            a1 = bot_v18_mod.agent(obs1)
            env.step([a0, a1])
        r0 = float(env.state[0].reward)
        r1 = float(env.state[1].reward)
        print(f"  {name:<35}: D.1=${r0:,.0f} vs Opp=${r1:,.0f} | Margin=${r0-r1:+,.0f} | Won={r0>r1}")

for s in [1000, 42, 20042]:
    test_seed(s)
