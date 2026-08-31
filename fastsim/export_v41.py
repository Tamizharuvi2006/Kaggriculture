import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import generalization_pipeline.submission_candidate_competitive_hybrid_v4 as v41

os.makedirs("fastsim/data", exist_ok=True)
out_path = "fastsim/data/v41_full_runtime.json"
with open(out_path, "w") as f:
    json.dump(v41._V18_RUNTIME, f)

print(f"Exported full V4.1 runtime to {out_path} ({os.path.getsize(out_path)} bytes)")
