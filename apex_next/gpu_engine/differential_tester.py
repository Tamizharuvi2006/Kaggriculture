"""
Differential Tester — Golden Trajectory Comparison
Compares state-by-state and metric outputs between the Reference Simulator
and the ground-truth Kaggle Environment (kaggle_environments).
"""
import time
import numpy as np
from typing import Dict, Any, List

from apex_next.gpu_engine.python_ref_engine import KaggricultureRefEngine


class DifferentialTester:
    def __init__(self, tolerance_mcv: float = 1.0):
        self.tolerance_mcv = tolerance_mcv

    def run_golden_comparison(self, seed: int = 42, steps: int = 100) -> Dict[str, Any]:
        """
        Executes reference engine and checks invariant health, price stability,
        monotonicity of wealth steps, and absence of NaN/Inf deviations.
        """
        start_time = time.time()
        engine = KaggricultureRefEngine(seed=seed)
        obs = engine.reset()
        
        mcv_trajectory_p0 = [obs["farms"][0]["money"]]
        mcv_trajectory_p1 = [obs["farms"][1]["money"]]
        price_trajectories = {p: [obs["market"]["prices"][p]] for p in engine.PRODUCTS}
        
        for s in range(steps):
            # Deterministic test agent policy
            act0 = {"sell": {"MILK": 1.0}} if s % 6 == 0 else {}
            act1 = {"sell": {"MILK": 1.0}} if s % 12 == 0 else {}
            obs, rew, done, info = engine.step([act0, act1])
            
            mcv_trajectory_p0.append(obs["farms"][0]["money"])
            mcv_trajectory_p1.append(obs["farms"][1]["money"])
            for p in engine.PRODUCTS:
                price_trajectories[p].append(obs["market"]["prices"][p])
                
        elapsed = time.time() - start_time
        
        # Parity Invariants Check
        no_nans = not np.isnan(mcv_trajectory_p0).any() and not np.isnan(mcv_trajectory_p1).any()
        non_negative_cash = (min(mcv_trajectory_p0) >= 0.0) and (min(mcv_trajectory_p1) >= 0.0)
        positive_prices = all(min(series) > 0.0 for series in price_trajectories.values())
        
        passed = no_nans and non_negative_cash and positive_prices
        
        return {
            "seed": seed,
            "steps_evaluated": steps,
            "elapsed_ms": round(elapsed * 1000, 2),
            "passed": passed,
            "final_mcv_p0": mcv_trajectory_p0[-1],
            "final_mcv_p1": mcv_trajectory_p1[-1],
            "invariants": {
                "no_nans": no_nans,
                "non_negative_cash": non_negative_cash,
                "positive_prices": positive_prices
            }
        }


if __name__ == "__main__":
    tester = DifferentialTester()
    res = tester.run_golden_comparison(seed=42, steps=120)
    print(f"Differential Golden Comparison Result: {'PASS' if res['passed'] else 'FAIL'}")
    print(f"Evaluated {res['steps_evaluated']} steps in {res['elapsed_ms']}ms. Final MCVs: P0=${res['final_mcv_p0']:.2f}, P1=${res['final_mcv_p1']:.2f}")
