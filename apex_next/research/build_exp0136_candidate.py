"""
Build Candidate Submission for EXP-0136 (CAND-136-02: 5 Cows + 0 Sheep)
Modifies Day 0/1 Opening Action Schedule:
- Step 0: ['BUY_ANIMAL', 'COW', 5] (instead of 3)
- Step 1: Removes ['BUY_ANIMAL', 'SHEEP', 1]
Encodes updated schedule into base85/zlib and produces:
- apex_next/research/EXP-0136/candidate/candidate_submission.py
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
    print("[EXP-0136] BUILDING CANDIDATE SUBMISSION (CAND-136-02: 5 COWS + 0 SHEEP)")
    print("==========================================================================\n")
    
    # 1. Decode production baseline schedule
    raw = base64.b85decode(_FIXED_SCHEDULE_B85)
    decomp = zlib.decompress(raw).decode("utf-8")
    schedule = json.loads(decomp)
    
    # 2. Modify Step 0 and Step 1 actions
    # Step 0: Replace ['BUY_ANIMAL', 'COW', 3] with ['BUY_ANIMAL', 'COW', 5]
    step0_market = []
    for m in schedule[0].get("market", []):
        if m[0] == "BUY_ANIMAL" and m[1] == "COW":
            step0_market.append(["BUY_ANIMAL", "COW", 5])
        else:
            step0_market.append(m)
    schedule[0]["market"] = step0_market
    
    # Step 1: Remove ['BUY_ANIMAL', 'SHEEP', 1]
    step1_market = []
    for m in schedule[1].get("market", []):
        if m[0] == "BUY_ANIMAL" and m[1] == "SHEEP":
            continue # Remove sheep purchase
        else:
            step1_market.append(m)
    schedule[1]["market"] = step1_market
    
    # 3. Compress modified schedule
    new_json_str = json.dumps(schedule, separators=(",", ":"))
    new_compressed = zlib.compress(new_json_str.encode("utf-8"), level=9)
    new_b85_str = base64.b85encode(new_compressed).decode("utf-8")
    
    # 4. Load baseline submission.py template
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    # Replace _FIXED_SCHEDULE_B85 with new_b85_str
    import re
    pattern = r'_FIXED_SCHEDULE_B85 = \(\s*("[\s\S]*?")\s*\)'
    
    # Split new_b85_str into 100-character string literal chunks
    chunk_size = 100
    chunks = [new_b85_str[i:i+chunk_size] for i in range(0, len(new_b85_str), chunk_size)]
    formatted_chunks = "(\n    " + "\n    ".join([f'"{c}"' for c in chunks]) + "\n)"
    
    new_code = re.sub(pattern, f'_FIXED_SCHEDULE_B85 = {formatted_chunks}', code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0136", "candidate")
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
