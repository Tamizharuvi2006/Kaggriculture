"""
Build Candidate Submission for EXP-0151 (CAND-151-02: Semantic Task Coordinator with Protected Pasture Invariant)
Modifies submission.py:
1. Implements Semantic Task Graph protection inside _apply_fixed_board_adaptation():
   - Strictly locks Hands 0, 1, 2, 3 (ensuring Step 159 Pasture 2 BUILD and Step 170 Cow PICKUP execute with 100% fidelity).
   - Dynamically allocates unreserved Hand 4 / 5 (workers >= index 4 with PASS actions) to till and plant SW quadrant.
   - Reconciles worker position back to anchor before step 171.
Produces:
- apex_next/research/EXP-0151/candidate/candidate_submission.py
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


def build_candidate():
    print("==========================================================================")
    print("[EXP-0151] BUILDING CANDIDATE SUBMISSION (CAND-151-02: SEMANTIC COORDINATOR)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    semantic_hook_code = '''def _apply_fixed_board_adaptation(obs, action):
    """Observation-only adaptation with Semantic Task Graph protection for critical infrastructure."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    # EXP-0151 SPATIAL_POLICY-3: Semantic Task Coordination
    # 1. Step 75 Melon Liquidity Conversion
    if step == 75:
        copied["market"].append(["SELL", "MELON", 6])
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # 2. Step 152 Dynamic Land 2 Expansion
    if step == 152:
        copied["market"].append(["BUY_LAND"])

    # 3. Semantic Task Allocation for Unreserved Workers (Index >= 4)
    # INVARIANT: Hands 0, 1, 2, 3 are CRITICAL MILESTONES (Pasture 2 @ Step 159, Cow Pickup @ Step 170) -> NEVER TOUCHED!
    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", [0]) or [0]
    if len(unlocked) >= 2 and 153 <= step <= 170:
        hands = copied.get("hands", [])
        for w_idx in range(4, len(hands)):
            if hands[w_idx] == ["PASS"] or hands[w_idx] == "PASS":
                if step in (153, 154, 155):
                    copied["hands"][w_idx] = ["SOUTH"]
                elif step in (156, 157):
                    copied["hands"][w_idx] = ["TILL"]
                elif step in (158, 159):
                    copied["hands"][w_idx] = ["PLANT", "STRAWBERRY"]
                elif step in (160, 161):
                    copied["hands"][w_idx] = ["WATER"]
                elif step in (165, 166, 167):
                    copied["hands"][w_idx] = ["NORTH"]

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, semantic_hook_code, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0151", "candidate")
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
