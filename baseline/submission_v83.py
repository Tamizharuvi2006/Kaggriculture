"""V8.3 Baseline Master Submission: Opponent Supply-Aware Market Ranker.

Official Benchmark Score: $184,404.03 (across 100 seeds, 0 Bankruptcies, $7,666.31 StdDev)
Net Gain over V8.2 Baseline: +$59,650.05 ($124.75k -> $184.40k)
"""

import os
import sys
import importlib.util

V83_OPP_PATH = os.path.join(os.path.dirname(__file__), "submission_v83_opponent_aware.py")
spec = importlib.util.spec_from_file_location("v83_sub", V83_OPP_PATH)
v83 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v83)

agent = v83.agent
