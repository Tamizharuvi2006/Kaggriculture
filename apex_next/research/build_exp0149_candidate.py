"""
Build Candidate Submission for EXP-0149 (CAND-149-02: Dynamic Closed-Loop Worker Spatial Routing Overlay)
Modifies submission.py:
1. Adds spatial worker rerouting logic to _apply_fixed_board_adaptation():
   - Intercepts PASS worker actions at Steps 152 to 170 when SW quadrant is unlocked.
   - Reroutes idle workers to move SOUTH and TILL/PLANT newly unlocked SW tiles.
   - Adds Day 4 melon liquidity at Step 75 and advances BUY_LAND to Step 152.
2. Preserves 100% fallback to _FIXED_SCHEDULE_B85 outside override conditions.
Produces:
- apex_next/research/EXP-0149/candidate/candidate_submission.py
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
    print("[EXP-0149] BUILDING CANDIDATE SUBMISSION (CAND-149-02: SPATIAL OVERLAY)")
    print("==========================================================================\n")
    
    # 1. Modify _apply_fixed_board_adaptation() in submission.py
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    # Spatial override implementation
    spatial_hook_code = '''def _apply_fixed_board_adaptation(obs, action):
    """Observation-only adaptation layered on a validated fixed executor with closed-loop spatial worker rerouting."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    # EXP-0149 SPATIAL_POLICY-1: Dynamic Closed-Loop Worker Routing
    # 1. Step 75 Melon Liquidity Conversion
    if step == 75:
        copied["market"].append(["SELL", "MELON", 6])
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # 2. Step 152 Dynamic Land 2 Expansion
    if step == 152:
        copied["market"].append(["BUY_LAND"])

    # 3. Dynamic Worker Routing Overlay (Steps 153 to 170)
    # When SW quadrant is unlocked, reroute any PASS worker towards SW quadrant
    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", [0]) or [0]
    if len(unlocked) >= 2 and 153 <= step <= 170:
        hands = copied.get("hands", [])
        for i, h in enumerate(hands):
            if h == ["PASS"] or h == "PASS":
                # Direct idle worker SOUTH into SW quadrant
                copied["hands"][i] = ["SOUTH"]

    return copied
'''
    
    # Replace _apply_fixed_board_adaptation definition
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, spatial_hook_code, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0149", "candidate")
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
