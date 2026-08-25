"""High-Performance Multi-Core Parallel Tournament Engine.
Leverages all physical/logical CPU cores via ProcessPoolExecutor for 10x-15x evaluation speedups.
"""
from __future__ import annotations
import os
import sys
import concurrent.futures
from typing import Dict, Any, List, Callable, Tuple
import kaggle_environments

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def _run_single_pair_worker(args: Tuple[str, str, int, int]) -> Dict[str, Any]:
    """Top-level worker function for clean multiprocessing pickling on Windows."""
    import importlib.util

    cand_module_path, opp_module_path, seed, steps = args

    # Dynamically load fresh modules per process
    spec_cand = importlib.util.spec_from_file_location("cand_mod", cand_module_path)
    cand_mod = importlib.util.module_from_spec(spec_cand)
    spec_cand.loader.exec_module(cand_mod)

    spec_opp = importlib.util.spec_from_file_location("opp_mod", opp_module_path)
    opp_mod = importlib.util.module_from_spec(spec_opp)
    spec_opp.loader.exec_module(opp_mod)

    cand_agent = cand_mod.agent if hasattr(cand_mod, "agent") else cand_mod.VariantDAgent().act
    opp_agent = opp_mod.agent

    # Match 1: Candidate = Seat 0, Opponent = Seat 1
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env1.reset()
    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        env1.step([cand_agent(obs0), opp_agent(obs1)])

    c_s0 = float(env1.state[0].reward or 0.0)
    o_s1 = float(env1.state[1].reward or 0.0)
    m1_win = 1.0 if c_s0 > o_s1 else (0.5 if c_s0 == o_s1 else 0.0)

    # Match 2: Opponent = Seat 0, Candidate = Seat 1
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env2.reset()
    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        env2.step([opp_agent(obs0), cand_agent(obs1)])

    o_s0 = float(env2.state[0].reward or 0.0)
    c_s1 = float(env2.state[1].reward or 0.0)
    m2_win = 1.0 if c_s1 > o_s0 else (0.5 if c_s1 == o_s0 else 0.0)

    paired_delta = (c_s0 + c_s1) - (o_s0 + o_s0)

    return {
        "seed": seed,
        "cand_seat0": c_s0,
        "opp_seat1": o_s1,
        "m1_win": m1_win,
        "opp_seat0": o_s0,
        "cand_seat1": c_s1,
        "m2_win": m2_win,
        "paired_delta": (c_s0 + c_s1) - (o_s0 + o_s1),
    }

class ParallelTournament:
    """Executes paired matches concurrently across all CPU cores."""

    @staticmethod
    def run_parallel_gauntlet(
        cand_module_path: str,
        opp_module_path: str,
        seeds: List[int],
        steps: int = 720,
        max_workers: int | None = None,
    ) -> Dict[str, Any]:
        if max_workers is None:
            max_workers = min(32, os.cpu_count() or 4)

        worker_args = [(cand_module_path, opp_module_path, s, steps) for s in seeds]

        results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            for res in executor.map(_run_single_pair_worker, worker_args):
                results.append(res)

        # Sort results by original seed order
        results.sort(key=lambda x: seeds.index(x["seed"]))

        total_matches = len(seeds) * 2
        total_wins = sum(r["m1_win"] + r["m2_win"] for r in results)
        seat0_wins = sum(r["m1_win"] for r in results)
        seat1_wins = sum(r["m2_win"] for r in results)
        total_delta = sum(r["paired_delta"] for r in results)

        return {
            "num_seeds": len(seeds),
            "total_matches": total_matches,
            "overall_win_rate": round(total_wins / total_matches, 4) if total_matches > 0 else 0.0,
            "seat0_win_rate": round(seat0_wins / len(seeds), 4) if seeds else 0.0,
            "seat1_win_rate": round(seat1_wins / len(seeds), 4) if seeds else 0.0,
            "mean_paired_delta": round(total_delta / len(seeds), 2) if seeds else 0.0,
            "total_delta": round(total_delta, 2),
            "detailed_results": results,
        }
