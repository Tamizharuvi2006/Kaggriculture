"""
Build Candidate Submission for EXP-0154 (CAND-154-02: Worker #3 Post-Pasture SW Allocation)
Modifies submission.py:
1. Implements Worker #3 Post-Pasture SW Cultivation in _apply_fixed_board_adaptation():
   - Step 75: ['SELL', 'MELON', 6] + ['BUY_SEED', 'STRAWBERRY', 6]
   - Step 152: ['BUY_LAND']
   - Step 159: Worker #2 & Worker #3 BUILD_PASTURE (100% Protected Milestone).
   - Steps 160-167: Worker #3 detours South, tills/plants SW strawberry tile, and returns North to anchor (3, 4).
   - Step 170: Worker #0 Cow Pickup (100% Protected Milestone).
   - Step 171: Zero coordinate drift at schedule resumption.
Produces:
- apex_next/research/EXP-0154/candidate/candidate_submission.py
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
    print("[EXP-0154] BUILDING CANDIDATE SUBMISSION (CAND-154-02: WORKER #3 POST-PASTURE)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    worker3_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """Worker #3 Post-Pasture SW Allocation with 100% Critical Milestone Protection."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", [0]) or [0]
    shed = own_farm.get("inventory", {}) or {}
    money = float(_get(own_farm, "money", 0.0) or 0.0)

    # 1. Market Liquidations & Expansions
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    # 2. Worker #3 Post-Pasture Detour (Steps 160 to 167)
    # INVARIANT: Step 159 Pasture 2 Build by Workers #2 & #3 is 100% UNTOUCHED!
    # INVARIANT: Step 170 Cow Pickup by Worker #0 is 100% UNTOUCHED!
    if len(unlocked) >= 2 and 160 <= step <= 167:
        hands = copied.get("hands", [])
        if len(hands) >= 4:
            # Worker #3 (index 3) executes detour AFTER Pasture 2 is built @ Step 159
            if step in (160, 161):
                copied["hands"][3] = ["SOUTH"]
            elif step == 162:
                copied["hands"][3] = ["TILL"]
            elif step == 163:
                copied["hands"][3] = ["PLANT", "STRAWBERRY"]
            elif step == 164:
                copied["hands"][3] = ["WATER"]
            elif step in (165, 166):
                copied["hands"][3] = ["NORTH"]
            elif step == 167:
                copied["hands"][3] = ["PASS"]  # Arrived at anchor (3, 4)

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, worker3_hook, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0154", "candidate")
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
