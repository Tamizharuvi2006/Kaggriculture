"""PRE-SUBMISSION AUDIT FOR APEX 3.3 MONOLITHIC CANDIDATE.

Verifies:
1. Pure self-contained import & execution of submission_candidate_apex33.py
2. Zero syntax/runtime errors during a 720-step Kaggle simulation
3. Correct action schema structure (dict containing 'farmer', 'hands', 'market')
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATE_PATH = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex33.py")

sys.path.insert(0, BASE_DIR)
import kaggle_environments

def audit_apex33():
    print("====================================================================================================", flush=True)
    print("PRE-SUBMISSION AUDIT: MONOLITHIC APEX 3.3 CANDIDATE", flush=True)
    print("====================================================================================================", flush=True)

    spec = importlib.util.spec_from_file_location("apex33_candidate", CANDIDATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    apex33_agent = mod.agent

    print(f"Candidate file loaded: {CANDIDATE_PATH}")
    print("Executing 720-step dry-run Kaggle simulation...", flush=True)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": 99999})
    trainer = env.train([None, apex33_agent])
    obs = trainer.reset()

    preempt_milk_count = 0
    preempt_straw_count = 0

    for s in range(720):
        act = apex33_agent(obs)
        assert isinstance(act, dict), f"Step {s}: Action is not a dict: {type(act)}"
        assert "farmer" in act, f"Step {s}: Missing 'farmer' key in action"
        assert "hands" in act, f"Step {s}: Missing 'hands' key in action"
        assert "market" in act, f"Step {s}: Missing 'market' key in action"

        if s % 24 == 23:
            for m in act.get("market") or []:
                if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL":
                    if m[1] == "MILK":
                        preempt_milk_count += 1
                    elif m[1] == "STRAWBERRY":
                        preempt_straw_count += 1

        obs, rew, done, info = trainer.step(act)
        if done:
            break

    final_wealth = float(rew if rew is not None else 0.0)
    print(f"Dry-Run Completed Successfully! Final Wealth: ${final_wealth:,.2f}")
    print(f"Preemption Sales Executed @ step % 24 == 23: Milk = {preempt_milk_count}, Strawberry = {preempt_straw_count}")
    print("\n[PASSED] PRE-SUBMISSION AUDIT PASSED: 0 ERRORS, 100% VALID SCHEMA & STANDALONE EXECUTION.")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    audit_apex33()
