"""V8.4 Experimental Development Branch.

Inherits from V8.3 Champion Baseline (submission_v83.py).
All future experimental work and macro-strategy exploration will occur in this file,
leaving baseline/submission_v83.py permanently frozen as the Champion Baseline.
"""

import os
import sys
import importlib.util

V83_CHAMPION_PATH = os.path.join(os.path.dirname(__file__), "submission_v83.py")
spec = importlib.util.spec_from_file_location("v83_champ", V83_CHAMPION_PATH)
v83 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v83)

agent = v83.agent
