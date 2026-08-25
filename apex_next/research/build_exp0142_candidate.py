"""
Build Candidate Submission for EXP-0142 (CAND-142-02: Adaptive Capital Priority = True)
Modifies DEFAULT_STRATEGY in submission.py:
- "adaptive_capital_priority": True
Produces:
- apex_next/research/EXP-0142/candidate/candidate_submission.py
"""
import os
import sys
import re
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def build_candidate():
    print("==========================================================================")
    print("[EXP-0142] BUILDING CANDIDATE SUBMISSION (CAND-142-02: ADAPTIVE CAPITAL)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    # Replace "adaptive_capital_priority": False with "adaptive_capital_priority": True
    pattern = r'"adaptive_capital_priority":\s*False'
    new_code = re.sub(pattern, '"adaptive_capital_priority": True', code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0142", "candidate")
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
