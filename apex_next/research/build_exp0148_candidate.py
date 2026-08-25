"""
Build Candidate Submission for EXP-0148 (CAND-148-02: Day 4 Melon Liquidity & Land 2 Acceleration)
Modifies _FIXED_SCHEDULE_B85 in submission.py:
1. Step 75: Adds ['SELL', 'MELON', 6] + ['BUY_SEED', 'STRAWBERRY', 6] to market orders.
2. Step 152: Adds ['BUY_LAND'] (Land 2, $1,000) to market orders.
3. Step 170: Removes duplicate ['BUY_LAND'] from Step 170.
Produces:
- apex_next/research/EXP-0148/candidate/candidate_submission.py
"""
import os
import sys
import json
import zlib
import base64
import hashlib
import re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from generalization_pipeline.submission_candidate_apex35 import _FIXED_SCHEDULE_B85


def build_candidate():
    print("==========================================================================")
    print("[EXP-0148] BUILDING CANDIDATE SUBMISSION (CAND-148-02)")
    print("==========================================================================\n")
    
    # 1. Decode baseline schedule
    raw = base64.b85decode(_FIXED_SCHEDULE_B85)
    decomp = zlib.decompress(raw).decode("utf-8")
    schedule = json.loads(decomp)
    
    # 2. Modify Schedule
    # Step 75: Add SELL MELON 6 + BUY_SEED STRAWBERRY 6
    step75_market = schedule[75].get("market", [])
    step75_market.append(["SELL", "MELON", 6])
    step75_market.append(["BUY_SEED", "STRAWBERRY", 6])
    schedule[75]["market"] = step75_market
    
    # Step 152: Advance BUY_LAND
    step152_market = schedule[152].get("market", [])
    step152_market.append(["BUY_LAND"])
    schedule[152]["market"] = step152_market
    
    # Step 170: Remove BUY_LAND if present in market orders
    step170_market = schedule[170].get("market", [])
    step170_market = [m for m in step170_market if not (isinstance(m, list) and len(m) >= 1 and m[0] == "BUY_LAND")]
    schedule[170]["market"] = step170_market
    
    # 3. Compress modified schedule
    new_json = json.dumps(schedule, separators=(",", ":"))
    new_comp = zlib.compress(new_json.encode("utf-8"), level=9)
    new_b85 = base64.b85encode(new_comp).decode("ascii")
    
    # Format new_b85 as chunks of 100 characters inside parenthesized string
    chunks = [f'    "{new_b85[i:i+100]}"\n' for i in range(0, len(new_b85), 100)]
    new_b85_decl = "_FIXED_SCHEDULE_B85 = (\n" + "".join(chunks) + ")"
    
    # 4. Load baseline submission.py and replace _FIXED_SCHEDULE_B85
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    pattern = r'_FIXED_SCHEDULE_B85\s*=\s*\([^\)]+\)'
    new_code = re.sub(pattern, new_b85_decl, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0148", "candidate")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "candidate_submission.py")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(new_code)
        
    cand_hash = hashlib.sha256(new_code.encode("utf-8")).hexdigest()
    base_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    print(f"Baseline SHA-256 : {base_hash}")
    print(f"Candidate SHA-256: {cand_hash}")
    print(f"Generated candidate file: {out_file}\n")
    assert cand_hash != base_hash, "Candidate hash must be different from baseline hash!"
    return out_file, cand_hash


if __name__ == "__main__":
    build_candidate()
