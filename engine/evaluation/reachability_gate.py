"""Reachability Gate Protocol for Track B Research.
Verifies whether a candidate policy produces genuine physical state and market order divergences
from the Frozen Control (Variant D.1) before executing costly 64-match tournaments.
"""
from __future__ import annotations
import sys
import os
from typing import Callable, Dict, Any, List, Tuple
import kaggle_environments

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState

def extract_farm_telemetry(raw_obs, conf=None) -> Dict[str, Any]:
    """Extracts physical and economic farm telemetry for a given step."""
    obs = Observation(raw_obs, conf)
    farm = FarmState(obs)
    return {
        "step": obs.step,
        "day": obs.day,
        "money": farm.money,
        "num_workers": farm.num_workers,
        "num_cows": len(farm.animals_by_type.get("COW", [])),
        "num_sheep": len(farm.animals_by_type.get("SHEEP", [])),
        "num_crops": len(farm.plants),
        "shed_straw": farm.shed.get("STRAWBERRY", 0),
        "shed_milk": farm.shed.get("MILK", 0),
        "shed_wool": farm.shed.get("WOOL", 0),
        "shed_wheat": farm.shed.get("WHEAT", 0),
    }

def verify_reachability(candidate_agent_fn: Callable, candidate_name: str, seed: int = 42) -> Tuple[bool, Dict[str, Any]]:
    """Runs a single 720-step verification match comparing Candidate vs Control D.1."""
    print(f"\n[REACHABILITY GATE] Testing Candidate '{candidate_name}' on Seed {seed}...")

    # 1. Run Control D.1
    env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_ctrl.reset()
    agent_ctrl = VariantDAgent()
    
    ctrl_telemetry: List[Dict[str, Any]] = []
    ctrl_actions: List[Any] = []

    while not env_ctrl.done:
        raw_obs0 = env_ctrl.state[0].observation
        t_ctrl = extract_farm_telemetry(raw_obs0, env_ctrl.configuration)
        ctrl_telemetry.append(t_ctrl)
        
        act0 = agent_ctrl.act(raw_obs0, env_ctrl.configuration)
        act1 = bot_v18.agent(env_ctrl.state[1].observation)
        ctrl_actions.append(act0)
        env_ctrl.step([act0, act1])

    # 2. Run Candidate
    env_cand = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_cand.reset()
    
    cand_telemetry: List[Dict[str, Any]] = []
    cand_actions: List[Any] = []

    while not env_cand.done:
        raw_obs0 = env_cand.state[0].observation
        t_cand = extract_farm_telemetry(raw_obs0, env_cand.configuration)
        cand_telemetry.append(t_cand)
        
        act0 = candidate_agent_fn(raw_obs0, env_cand.configuration)
        act1 = bot_v18.agent(env_cand.state[1].observation)
        cand_actions.append(act0)
        env_cand.step([act0, act1])

    # 3. Compare Trajectories at Key Days (1, 5, 10, 15, 20, 25, 29)
    check_steps = [24, 120, 240, 360, 480, 600, 696]
    divergences = 0
    total_checks = len(check_steps)

    print("-" * 95)
    print(f"{'Day (Step)':<12} | {'Control State (Cows/Sheep/Crops/Workers)':<42} | {'Candidate State (Cows/Sheep/Crops/Workers)':<42}")
    print("-" * 95)

    for step_idx in check_steps:
        if step_idx < len(ctrl_telemetry) and step_idx < len(cand_telemetry):
            c_t = ctrl_telemetry[step_idx]
            k_t = cand_telemetry[step_idx]
            
            c_str = f"Cows:{c_t['num_cows']} | Sheep:{c_t['num_sheep']} | Crops:{c_t['num_crops']} | W:{c_t['num_workers']}"
            k_str = f"Cows:{k_t['num_cows']} | Sheep:{k_t['num_sheep']} | Crops:{k_t['num_crops']} | W:{k_t['num_workers']}"
            
            is_diff = (c_t['num_cows'] != k_t['num_cows'] or 
                       c_t['num_sheep'] != k_t['num_sheep'] or 
                       c_t['num_crops'] != k_t['num_crops'] or 
                       c_t['num_workers'] != k_t['num_workers'])
            
            if is_diff:
                divergences += 1
            print(f"Day {c_t['day']:>2} ({step_idx:>3}) | {c_str:<42} | {k_str:<42} {'[DIFF]' if is_diff else '[IDENTICAL]'}")

    print("-" * 95)

    # 4. Action Level Divergence Rate
    action_divergence_steps = sum(1 for a_c, a_k in zip(ctrl_actions, cand_actions) if a_c != a_k)
    action_divergence_pct = (action_divergence_steps / len(ctrl_actions)) * 100.0

    print(f"Total Action Divergence Steps : {action_divergence_steps} / {len(ctrl_actions)} ({action_divergence_pct:.1f}%)")
    print(f"State Milestone Divergence     : {divergences} / {total_checks} milestones")

    passed = (divergences > 0 or action_divergence_pct > 1.0)
    print(f"REACHABILITY VERDICT           : {'PASSED [OK] (Knob is Live & Differentiated)' if passed else 'FAILED [X] (Knob is INERT / 100% Identical to Control)'}")
    print("-" * 95)

    return passed, {
        "candidate_name": candidate_name,
        "action_divergence_pct": action_divergence_pct,
        "milestone_divergences": divergences,
        "passed": passed,
    }
