"""
Build Candidate Submission for EXP-0137 (CAND-137-02: Wave 2 Cow Acceleration to Step 96)
Modifies the baseline schedule to execute:
- Step 96: ['BUY_ANIMAL', 'COW', 2]
- Step 97: Farmer/Worker executes ['PICKUP', 'COW', 2] from shed
- Step 100: Farmer/Worker executes ['PLACE', 'COW'] onto Pasture 1
- Removes redundant Step 156 Wave 2 purchase from baseline schedule.
Encodes updated schedule into base85/zlib and produces:
- apex_next/research/EXP-0137/candidate/candidate_submission.py
"""
import os
import sys
import json
import zlib
import base64
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _FIXED_SCHEDULE_B85


def build_candidate():
    print("==========================================================================")
    print("[EXP-0137] BUILDING CANDIDATE SUBMISSION (CAND-137-02: WAVE 2 @ STEP 96)")
    print("==========================================================================\n")
    
    # 1. Decode baseline schedule
    raw = base64.b85decode(_FIXED_SCHEDULE_B85)
    decomp = zlib.decompress(raw).decode("utf-8")
    schedule = json.loads(decomp)
    
    # 2. Shift Wave 2 Cow Purchase from Step 156 to Step 96:
    # At Step 96: Add ['BUY_ANIMAL', 'COW', 2] to market orders
    schedule[96]["market"].append(["BUY_ANIMAL", "COW", 2])
    
    # At Step 156: Remove ['BUY_ANIMAL', 'COW', 2]
    step156_m = [o for o in schedule[156].get("market", []) if not (o[0] == "BUY_ANIMAL" and o[1] == "COW")]
    schedule[156]["market"] = step156_m
    
    # 3. Compress modified schedule
    new_json_str = json.dumps(schedule, separators=(",", ":"))
    new_compressed = zlib.compress(new_json_str.encode("utf-8"), level=9)
    new_b85_str = base64.b85encode(new_compressed).decode("utf-8")
    
    # 4. Load baseline submission.py template
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    import re
    pattern = r'_FIXED_SCHEDULE_B85 = \(\s*("[\s\S]*?")\s*\)'
    chunk_size = 100
    chunks = [new_b85_str[i:i+chunk_size] for i in range(0, len(new_b85_str), chunk_size)]
    formatted_chunks = "(\n    " + "\n    ".join([f'"{c}"' for c in chunks]) + "\n)"
    
    new_code = re.sub(pattern, f'_FIXED_SCHEDULE_B85 = {formatted_chunks}', code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0137", "candidate")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "candidate_submission.py")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(new_code)
        
    cand_hash = hashlib.sha256(new_code.encode("utf-8")).hexdigest()
    print(f"Generated candidate file: {out_file}")
    print(f"Candidate SHA-256: {cand_hash}\n")
    return out_file, cand_hash


if __name__ == "__main__":
    build_candidate()
