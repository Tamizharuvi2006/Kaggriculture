"""L+ APEX 2.0: 4-Gate Evolution & Meta-Qualification Protocol.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, List, Any
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import kaggle_environments
    HAS_KAGGLE_ENV = True
except ImportError:
    HAS_KAGGLE_ENV = False

class ApexEvolutionLoop:
    """Manages autonomous candidate variant generation and 4-Gate validation:
    - GATE 0: Safety & Validity Audit (0 crashes, 0 corruptions, 0 bankruptcies)
    - GATE 1: Replay Reproduction (APEX >= L+ Control)
    - GATE 2: Statistical Supremacy (APEX > L+ Control with >= 75% Win Rate)
    - GATE 3: Current-Meta Qualification (APEX >= max(L+ Control, Ladder Benchmark Target))
    """

    def __init__(self, seeds: List[int], ladder_benchmark_target: float = 130000.0):
        self.seeds = seeds
        self.ladder_benchmark_target = ladder_benchmark_target
        self.control_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")

    def _load_agent(self, filepath: str, name: str):
        spec = importlib.util.spec_from_file_location(name, filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent

    def evaluate_candidate(self, candidate_path: str, candidate_name: str) -> Dict[str, Any]:
        if not HAS_KAGGLE_ENV:
            return {"error": "Kaggle environment unavailable"}

        control_fn = self._load_agent(self.control_path, f"ctrl_{candidate_name}")
        cand_fn = self._load_agent(candidate_path, f"cand_{candidate_name}")
        opp_fn = self._load_agent(os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"), f"opp_{candidate_name}")

        control_scores = []
        cand_scores = []
        errors = 0
        bankruptcies = 0
        wins = 0

        for seed in self.seeds:
            try:
                env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
                env_ctrl.run([control_fn, opp_fn])
                ctrl_val = float(env_ctrl.steps[-1][0]["observation"]["farms"][0]["money"])
            except Exception:
                ctrl_val = 0.0
            control_scores.append(ctrl_val)

            try:
                env_cand = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
                env_cand.run([cand_fn, opp_fn])
                cand_val = float(env_cand.steps[-1][0]["observation"]["farms"][0]["money"])
            except Exception as e:
                cand_val = 0.0
                errors += 1

            cand_scores.append(cand_val)
            if cand_val < 10000.0:
                bankruptcies += 1
            if cand_val >= ctrl_val:
                wins += 1

        avg_ctrl = sum(control_scores) / max(1, len(control_scores))
        avg_cand = sum(cand_scores) / max(1, len(cand_scores))

        gate0_pass = (errors == 0) and (bankruptcies == 0)
        gate1_pass = gate0_pass and (avg_cand >= avg_ctrl)
        gate2_pass = gate1_pass and (avg_cand > avg_ctrl) and (wins >= len(self.seeds) * 0.75)
        
        # Gate 3: Dynamic Current-Meta Threshold
        benchmark_target = max(avg_ctrl + 2000.0, self.ladder_benchmark_target)
        gate3_pass = gate2_pass and (avg_cand >= benchmark_target)

        return {
            "candidate": candidate_name,
            "seeds_tested": len(self.seeds),
            "avg_control": avg_ctrl,
            "avg_candidate": avg_cand,
            "net_delta": avg_cand - avg_ctrl,
            "errors": errors,
            "bankruptcies": bankruptcies,
            "gate0_safety_pass": gate0_pass,
            "gate1_replay_pass": gate1_pass,
            "gate2_stat_pass": gate2_pass,
            "gate3_meta_qualify": gate3_pass,
        }
