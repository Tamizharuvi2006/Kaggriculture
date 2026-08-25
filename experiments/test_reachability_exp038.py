"""Reachability Test of EXP038 Portfolio Profiles.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.evaluation.reachability_gate import verify_reachability
from experiments.exp038_policy_portfolio import make_portfolio_agent

def test_reachability():
    print("=" * 95)
    print("TESTING REACHABILITY ON EXP038 PORTFOLIO PROFILES")
    print("=" * 95)

    p2 = make_portfolio_agent("DAIRY_INDUSTRIALIST")
    verify_reachability(p2, "EXP038 Profile 2: Dairy Industrialist (Cows + Sheep)")

    p3 = make_portfolio_agent("FAST_TURNOVER")
    verify_reachability(p3, "EXP038 Profile 3: Fast-Turnover Cash")

if __name__ == "__main__":
    test_reachability()
