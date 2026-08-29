"""Audit script to test D.1 Control vs D.1.1 Bugfix against multiple baseline bots."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import kaggle_environments

# Load D.1 Control
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load D.1.1 Bugfix
spec_fix = importlib.util.spec_from_file_location("sub_fix", os.path.join(BASE_DIR, "submission_bugfix.py"))
sub_fix = importlib.util.module_from_spec(spec_fix)
spec_fix.loader.exec_module(sub_fix)

# Load Benchmarks
def load_bot(path):
    spec = importlib.util.spec_from_file_location("bot", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

bots = {
    "Kaito-V18": load_bot(os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")),
    "V8.1": load_bot(os.path.join(BASE_DIR, "baseline", "submission_v81.py")),
    "V8.2": load_bot(os.path.join(BASE_DIR, "baseline", "submission_v82.py")),
    "V8.3": load_bot(os.path.join(BASE_DIR, "baseline", "submission_v83.py")),
}

seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042]

print("=" * 100)
print(f"{'Bot Opponent':<15} | {'Seed':<6} | {'D.1 (Control)':<18} | {'D.1.1 (Bugfix)':<18} | {'Delta ($)':<12} | {'Verdict'}")
print("=" * 100)

for bot_name, bot_mod in bots.items():
    d1_wins = 0
    fix_wins = 0
    deltas = []
    
    for s in seeds:
        # Run D.1 Control
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env_ctrl.reset()
        while not env_ctrl.done:
            obs0 = env_ctrl.state[0].observation
            obs1 = env_ctrl.state[1].observation
            a0 = sub_d1.agent(obs0, env_ctrl.configuration)
            try:
                a1 = bot_mod.agent(obs1, env_ctrl.configuration)
            except TypeError:
                a1 = bot_mod.agent(obs1)
            env_ctrl.step([a0, a1])
        r_ctrl = float(env_ctrl.state[0].reward)
        r_opp_ctrl = float(env_ctrl.state[1].reward)
        ctrl_won = r_ctrl > r_opp_ctrl

        # Run D.1.1 Bugfix
        env_fix = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env_fix.reset()
        while not env_fix.done:
            obs0 = env_fix.state[0].observation
            obs1 = env_fix.state[1].observation
            a0 = sub_fix.agent(obs0, env_fix.configuration)
            try:
                a1 = bot_mod.agent(obs1, env_fix.configuration)
            except TypeError:
                a1 = bot_mod.agent(obs1)
            env_fix.step([a0, a1])
        r_fix = float(env_fix.state[0].reward)
        r_opp_fix = float(env_fix.state[1].reward)
        fix_won = r_fix > r_opp_fix
        
        delta = r_fix - r_ctrl
        deltas.append(delta)
        if ctrl_won: d1_wins += 1
        if fix_won: fix_wins += 1
        
        verdict = "WIN->WIN" if (ctrl_won and fix_won) else ("LOSS->WIN" if (not ctrl_won and fix_won) else ("WIN->LOSS" if (ctrl_won and not fix_won) else "LOSS->LOSS"))
        print(f"{bot_name:<15} | {s:<6} | ${r_ctrl:,.0f} vs ${r_opp_ctrl:,.0f} | ${r_fix:,.0f} vs ${r_opp_fix:,.0f} | ${delta:+10,.0f} | {verdict}")
    
    print(f"--> Summary vs {bot_name}: D.1 WR={d1_wins}/{len(seeds)} | D.1.1 WR={fix_wins}/{len(seeds)} | Mean Delta=${np.mean(deltas):+,.0f}")
    print("-" * 100)
