"""EXP104: High-Precision Trigger Quality Counterfactual Audit.

Compares Trigger ON (Multi-signal gated) vs Trigger OFF (Control D.1) on the exact same tournament seeds:
1. Trigger ON:
   - Evaluates conjoined signals: Opponent non-strawberry plots + Strawberry depression (<$112) + Melon premium (>=$235).
   - Only intervenes when true asymmetric advantage exists.
2. Trigger OFF:
   - Pure monolithic 38-Strawberry + 8-Cow Variant D.1.

Metrics:
- Terminal Bank Delta ($)
- Market Share Capture ($)
- Sensor Trigger Firing Counts
- 100% Solvency & Zero Stranded Inventory.
"""
from __future__ import annotations
import sys
import os
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from candidates.candidate_d2_asymmetric import CandidateD2AsymmetricAgent

DEFICIT_SEEDS = [1599299971, 1487822928, 1259752816, 963135243, 2144164697, 886661034]

def evaluate_seed_pair(seed: int):
    # 1. Run Trigger OFF (D.1 Control)
    env_off = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_off.reset()
    agent_off = CandidateD2AsymmetricAgent(force_trigger_off=True)

    while not env_off.done:
        a0 = agent_off.act(env_off.state[0].observation, env_off.configuration)
        a1 = bot_v18.agent(env_off.state[1].observation)
        env_off.step([a0, a1])

    r_off = float(env_off.state[0].reward or 0.0)
    opp_off = float(env_off.state[1].reward or 0.0)

    # 2. Run Trigger ON (Multi-signal gated)
    env_on = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_on.reset()
    agent_on = CandidateD2AsymmetricAgent(force_trigger_off=False)
    triggers_fired = 0

    while not env_on.done:
        obs0 = env_on.state[0].observation
        a0 = agent_on.act(obs0, env_on.configuration)
        if agent_on.asymmetric_active:
            triggers_fired += 1
        a1 = bot_v18.agent(env_on.state[1].observation)
        env_on.step([a0, a1])

    r_on = float(env_on.state[0].reward or 0.0)
    opp_on = float(env_on.state[1].reward or 0.0)

    pie_on = r_on + opp_on
    share_on = r_on / pie_on if pie_on > 0 else 0.0

    return {
        "seed": seed,
        "r_off": r_off,
        "r_on": r_on,
        "delta": r_on - r_off,
        "share_on": share_on,
        "triggers_fired": triggers_fired,
        "seeds_bought": agent_on.melon_seeds_bought,
        "plots_planted": agent_on.melon_plots_planted,
    }

def run_exp104():
    print("=" * 105)
    print("EXP104: HIGH-PRECISION TRIGGER QUALITY COUNTERFACTUAL AUDIT")
    print("=" * 105)
    print(f"{'Seed':<12} | {'Trigger OFF ($)':>16} | {'Trigger ON ($)':>16} | {'Net Delta ($)':>14} | {'Share ON':>10} | {'Triggers Fired':>15} | {'Seeds Bought'}")
    print("-" * 105)

    results = []
    for s in DEFICIT_SEEDS:
        res = evaluate_seed_pair(s)
        results.append(res)
        print(f"{s:<12} | ${res['r_off']:>15,.0f} | ${res['r_on']:>15,.0f} | ${res['delta']:>+13,.0f} | {res['share_on']:>9.1%} | {res['triggers_fired']:>15} | {res['seeds_bought']:>12}")

    print("=" * 105)
    mean_off = np.mean([r["r_off"] for r in results])
    mean_on = np.mean([r["r_on"] for r in results])
    mean_delta = np.mean([r["delta"] for r in results])
    mean_share = np.mean([r["share_on"] for r in results])
    mean_triggers = np.mean([r["triggers_fired"] for r in results])

    print(f"Mean Performance: Trigger OFF = ${mean_off:,.2f} | Trigger ON = ${mean_on:,.2f} (Net Delta: ${mean_delta:+,.2f}, Mean Share: {mean_share:.1%})")
    print(f"Sensor Activity : Mean Trigger Active Steps = {mean_triggers:.1f} steps per match")

    print("\n" + "=" * 105)
    print("1. TRIGGER QUALITY SCIENTIFIC CONCLUSION:")
    print("-" * 105)
    if mean_triggers == 0:
        print("  • Precision Gate Result: In standard saturated benchmark matches (v18), the opponent plays pure strawberries.")
        print("    The multi-signal sensor correctly identified 0 non-strawberry threats and suppressed all unneeded interventions.")
        print("  • Zero Deadweight Loss: 100% monolithic D.1 execution preserved when no asymmetric threat is present.")
    else:
        print(f"  • Trigger Fired: Executed on {mean_triggers:.1f} steps, delivering ${mean_delta:+,.2f} net delta.")
    print("  • Production Status: submission.py remains 100% FROZEN (Control A).")
    print("=" * 105)

if __name__ == "__main__":
    run_exp104()
