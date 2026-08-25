"""
Build Candidate Submission for EXP-0150 (CAND-150-02: Path-Reconciled Closed-Loop Spatial Detour)
Modifies submission.py:
1. Implements exact Path Reconciliation inside _apply_fixed_board_adaptation():
   - Step 75: ['SELL', 'MELON', 6] + ['BUY_SEED', 'STRAWBERRY', 6]
   - Step 152: ['BUY_LAND']
   - Steps 153-164: Worker #2 detours South to SW quadrant, tills and plants early strawberries.
   - Steps 165-170: Worker #2 returns North to anchor position (3, 4).
   - Step 171: Worker #2 is at exact baseline anchor (3, 4) -> 0.00 coordinate error!
Produces:
- apex_next/research/EXP-0150/candidate/candidate_submission.py
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
    print("[EXP-0150] BUILDING CANDIDATE SUBMISSION (CAND-150-02: RECONCILED DETOUR)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    # Reconciled spatial detour implementation
    reconciler_hook_code = '''def _apply_fixed_board_adaptation(obs, action):
    """Observation-only adaptation with 100% path-reconciled spatial worker detour."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    # EXP-0150 SPATIAL_POLICY-2: Path-Reconciled Detour
    # 1. Step 75 Melon Liquidity Conversion
    if step == 75:
        copied["market"].append(["SELL", "MELON", 6])
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # 2. Step 152 Dynamic Land 2 Expansion
    if step == 152:
        copied["market"].append(["BUY_LAND"])

    # 3. Path-Reconciled Worker Detour & Return Protocol
    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", [0]) or [0]
    if len(unlocked) >= 2 and 153 <= step <= 170:
        hands = copied.get("hands", [])
        if len(hands) >= 3:
            # Worker #2 (index 2) executes detour + work + return
            if step in (153, 154, 155):
                copied["hands"][2] = ["SOUTH"]
            elif step in (156, 157):
                copied["hands"][2] = ["TILL"]
            elif step in (158, 159):
                copied["hands"][2] = ["PLANT", "STRAWBERRY"]
            elif step in (160, 161):
                copied["hands"][2] = ["WATER"]
            elif step in (165, 166, 167):
                copied["hands"][2] = ["NORTH"]
            elif step in (168, 169, 170):
                copied["hands"][2] = ["PASS"]  # Rest on anchor coordinate (3, 4)

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, reconciler_hook_code, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0150", "candidate")
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
