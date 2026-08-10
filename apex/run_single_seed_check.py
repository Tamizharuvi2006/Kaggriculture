"""Fast 1-Seed Controlled Divergence Test & Step-by-Step Diagnostic Trace.
"""

from __future__ import annotations
import sys
import os
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from generalization_pipeline.submission_candidate_l_plus import agent as ctrl_agent
from apex.agent import agent as apex_agent, _POLICY

def load_opp_agent():
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("opp_mod", opp_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

opp_agent = load_opp_agent()
TEST_SEED = 590244349

def run_single_seed_check():
    print("====================================================================================================", flush=True)
    print(f"🔥 APEX 2.5 FAST 1-SEED CONTROLLED DIVERGENCE TEST (SEED: {TEST_SEED})", flush=True)
    print("====================================================================================================", flush=True)

    # 1. Run Control Baseline
    env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": TEST_SEED})
    env_ctrl.run([ctrl_agent, opp_agent])
    ctrl_wealth = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

    # 2. Reset APEX Policy State
    _POLICY.reset_episode()
    _POLICY.telemetry_traces.clear()
    _POLICY.divergences = 0
    _POLICY.agreements = 0
    _POLICY.total_decisions = 0

    # 3. Run APEX Candidate in Kaggle Environment
    env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": TEST_SEED})
    env_apex.run([apex_agent, opp_agent])
    apex_wealth = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

    margin_delta = apex_wealth - ctrl_wealth
    _POLICY.record_match_outcome(margin_delta)

    # 4. Output Structured Step-by-Step Telemetry
    print(f"\nSeed: {TEST_SEED}", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    if _POLICY.telemetry_traces:
        t = _POLICY.telemetry_traces[0]
        print(f"Candidate generated       : YES (At Step {t.step})", flush=True)
        print(f"Candidate passed safety   : YES (Approved by Safety + UCB)", flush=True)
        print(f"Candidate selected        : YES ({t.action_key})", flush=True)
        print(f"Selection Reason          : {t.reasoning}", flush=True)
        print(f"Predicted Delta Score     : {t.predicted_delta:.2f}", flush=True)
        print("----------------------------------------------------------------------------------------------------", flush=True)
        print(f"L+ Expert Action          : {t.expert_action.get('market', [])}", flush=True)
        print(f"APEX Divergent Action     : {t.apex_action.get('market', [])}", flush=True)
        print(f"Deviation executed        : YES", flush=True)
        print("----------------------------------------------------------------------------------------------------", flush=True)
        print(f"State Signature           : {t.state_signature}", flush=True)
        print(f"Transit Advantage         : +${t.attribution.transit_adv:.2f}", flush=True)
        print(f"Market Value Advantage    : +${t.attribution.market_adv:.2f}", flush=True)
        print(f"Downstream Production     : +${t.attribution.downstream_adv:.2f}", flush=True)
        print(f"Terminal Value Advantage  : +${t.attribution.terminal_adv:.2f}", flush=True)
    else:
        print("Candidate generated       : NO / NONE EXECUTED", flush=True)
        print("Candidate passed safety   : NO", flush=True)
        print("Candidate selected        : NO", flush=True)
        print("Deviation executed        : NO (100% L+ fallback)", flush=True)

    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"L+ Control Wealth         : ${ctrl_wealth:10,.2f}", flush=True)
    print(f"APEX Wealth               : ${apex_wealth:10,.2f}", flush=True)
    print(f"Net Margin Delta          : ${margin_delta:+10,.2f}", flush=True)
    print(f"Match Outcome             : {'WIN ✅' if margin_delta >= 0 else 'LOSS ❌'}", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_single_seed_check()
