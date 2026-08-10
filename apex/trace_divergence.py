"""Diagnostic script to trace why DivergenceController returned None for steps 100-600.
"""

from __future__ import annotations
import sys
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def trace_divergence_selection():
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    spec_a = importlib.util.spec_from_file_location("apex_mod", apex_path)
    apex_mod = importlib.util.module_from_spec(spec_a)
    spec_a.loader.exec_module(apex_mod)

    spec_o = importlib.util.spec_from_file_location("opp_mod", opp_path)
    opp_mod = importlib.util.module_from_spec(spec_o)
    spec_o.loader.exec_module(opp_mod)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})
    
    cand_count = 0
    approved_count = 0
    window_approved_count = 0

    for step_idx in range(720):
        obs = env.state[0]["observation"] if hasattr(env, "state") else {}
        # Run step trace
        act = apex_mod.agent(obs, env.configuration)
        
        policy_inst = apex_mod._POLICY
        # Trace candidate inspection
        if 100 <= step_idx <= 600:
            window_approved_count += 1

    print(f"Total Steps Inspected: 720", flush=True)

if __name__ == "__main__":
    trace_divergence_selection()
