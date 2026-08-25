"""EXP068: Track B (Final Historical Smoke-Fight Tournament).
Pits our permanently frozen champion Variant D.1 against all historical peak submissions:
Historical Roster:
1. V4.1 State-Repair Final (APEX41_SUBMISSION_FINAL.py - Historical Peak 1479.8)
2. APEX 3.0 Challenger (generalization_pipeline/submission_candidate_apex30.py - Historical 1116.5)
3. Competitive Hybrid V13 (generalization_pipeline/submission_candidate_aggressive_hybrid_v2.py - Historical 1058.6)
4. APEX 3.3 Challenger (generalization_pipeline/submission_candidate_apex33.py - Historical 1024.9)
5. APEX 4 PPO Final (APEX4_SUBMISSION_FINAL.py - Historical 971.6)
6. APEX 3.5 Prod (APEX35_ROLLBACK_ARCHIVE/submission_apex35_prod_backup.py - Historical 966.4)
7. V8.3 Monolithic (baseline/submission_v83_standalone.py - Historical 758.5)
8. kaitofukami-v18 (baseline/kaitofukami-v18.py - Benchmark Reference)

Phase 1 (Fast Knockout): 8 holdout seeds x 2 seats = 16 matches per challenger vs D.1.
Phase 2 (Full Gauntlet for Top Challengers): 32 holdout seeds x 2 seats = 64 matches.
"""
from __future__ import annotations
import sys
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

from engine.agent import VariantDAgent

# Helper to dynamically import challenger modules
def load_challenger_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BASE_DIR, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

CHALLENGERS = [
    ("V4.1 State-Repair (1479.8 Peak)", "APEX41_SUBMISSION_FINAL.py"),
    ("APEX 3.0 (1116.5)", "generalization_pipeline/submission_candidate_apex30.py"),
    ("Competitive Hybrid V13 (1058.6)", "generalization_pipeline/submission_candidate_aggressive_hybrid_v2.py"),
    ("APEX 3.3 (1024.9)", "generalization_pipeline/submission_candidate_apex33.py"),
    ("APEX 4 PPO Final (971.6)", "APEX4_SUBMISSION_FINAL.py"),
    ("APEX 3.5 Prod (966.4)", "APEX35_ROLLBACK_ARCHIVE/submission_apex35_prod_backup.py"),
    ("V8.3 Monolithic (758.5)", "baseline/submission_v83_standalone.py"),
    ("kaitofukami-v18 (Benchmark)", "baseline/kaitofukami-v18.py"),
]

def eval_single_challenger_match(args: tuple[str, str, int, int]) -> dict:
    """Evaluates 1 match between D.1 and a specific challenger on a seed and seat."""
    c_name, c_path, seed, d1_seat = args
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    agent_d1 = VariantDAgent()
    try:
        challenger_mod = load_challenger_module("c_mod_" + str(os.getpid()) + "_" + c_name[:4], c_path)
    except Exception as e:
        return {
            "challenger": c_name,
            "seed": seed,
            "d1_seat": d1_seat,
            "d1_bank": 0.0,
            "c_bank": 0.0,
            "margin": 0.0,
            "d1_win": False,
            "c_win": False,
            "is_tie": False,
            "error": str(e),
            "total_pie": 0.0,
        }

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        if d1_seat == 0:
            act0 = agent_d1.act(obs0, env.configuration)
            act1 = challenger_mod.agent(obs1, env.configuration) if "configuration" in challenger_mod.agent.__code__.co_varnames else challenger_mod.agent(obs1)
            env.step([act0, act1])
        else:
            act0 = challenger_mod.agent(obs0, env.configuration) if "configuration" in challenger_mod.agent.__code__.co_varnames else challenger_mod.agent(obs0)
            act1 = agent_d1.act(obs1, env.configuration)
            env.step([act0, act1])

    r_d1 = float(env.state[d1_seat].reward or 0.0)
    r_c = float(env.state[1 - d1_seat].reward or 0.0)

    return {
        "challenger": c_name,
        "seed": seed,
        "d1_seat": d1_seat,
        "d1_bank": r_d1,
        "c_bank": r_c,
        "margin": r_d1 - r_c,
        "d1_win": r_d1 > r_c,
        "c_win": r_c > r_d1,
        "is_tie": r_d1 == r_c,
        "error": None,
        "total_pie": r_d1 + r_c,
    }

def run_exp068():
    print("=" * 105)
    print("EXP068: FINAL HISTORICAL SMOKE-FIGHT TOURNAMENT (D.1 vs ALL HISTORICAL WINNERS)")
    print("=" * 105)

    knockout_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888]

    all_tasks = [
        (c_name, c_path, seed, seat)
        for c_name, c_path in CHALLENGERS
        for seed in knockout_seeds
        for seat in [0, 1]
    ]

    print(f"Running Phase 1 Fast Knockout ({len(all_tasks)} matches: 8 challengers x 8 seeds x 2 seats)...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        all_results = list(pool.map(eval_single_challenger_match, all_tasks))

    print("\n" + "=" * 105)
    print("PHASE 1 KNOCKOUT RESULTS: D.1 vs HISTORICAL SUBMISSION ROSTER")
    print("=" * 105)
    print(f"{'Challenger Version':<38} | {'D.1 Win %':>10} | {'D.1 Bank':>14} | {'Challenger Bank':>16} | {'Mean Margin':>14} | {'H2H Record'}")
    print("-" * 105)

    ranked_challengers = []

    for c_name, _ in CHALLENGERS:
        c_res = [r for r in all_results if r["challenger"] == c_name]
        d1_wins = sum(1 for r in c_res if r["d1_win"])
        c_wins = sum(1 for r in c_res if r["c_win"])
        ties = sum(1 for r in c_res if r["is_tie"])

        wr = (d1_wins + 0.5 * ties) / len(c_res)
        m_d1 = float(np.mean([r["d1_bank"] for r in c_res]))
        m_c = float(np.mean([r["c_bank"] for r in c_res]))
        m_mar = float(np.mean([r["margin"] for r in c_res]))

        ranked_challengers.append((c_name, wr, m_d1, m_c, m_mar, d1_wins, c_wins, ties))
        print(f"{c_name:<38} | {wr:>9.1%} | ${m_d1:>13,.2f} | ${m_c:>15,.2f} | ${m_mar:>+13,.2f} | {f'{d1_wins}W - {c_wins}L - {ties}T'}")

    print("=" * 105)

    # Autopsy
    v41_wr = next(wr for name, wr, _, _, _, _, _, _ in ranked_challengers if "V4.1" in name)
    print("\nFINAL SMOKE-FIGHT FORENSIC VERDICT:")
    if v41_wr >= 0.80:
        print(f"  >>> VERDICT: VARIANT D.1 DECISIVELY CRUSHES V4.1 (Win Rate = {v41_wr:.1%} vs 1479.8 Peak Bot!).")
        print("      V4.1's historical 1479.8 score was achieved against an early, non-saturated Kaggle ladder population.")
        print("      In direct head-to-head combat under identical conditions, Variant D.1 strictly dominates V4.1!")
    else:
        print("  >>> VERDICT: CHALLENGER IS COMPETITIVE. PROCEED TO FULL PHASE 2 GAUNTLET.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp068()
