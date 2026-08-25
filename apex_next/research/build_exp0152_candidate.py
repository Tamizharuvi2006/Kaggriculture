"""
Build Candidate Submission for EXP-0152 (CAND-152-02: Macro Semantic Task Coordinator)
Modifies submission.py:
1. Implements Full-Game Macro Semantic Task Coordination in _apply_fixed_board_adaptation():
   - Phase A: Day 4 Melon Liquidity -> Step 152 Land 2 -> Unreserved Worker SW Cultivation (with 100% Protected Step 159 Pasture 2).
   - Phase B: Hour 22 Pre-Clearance Liquidation (Captures peak daily market prices).
   - Phase C: Terminal Feed Conservation (Feeds cows from shed wheat, halting inflated town purchases).
Produces:
- apex_next/research/EXP-0152/candidate/candidate_submission.py
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
    print("[EXP-0152] BUILDING CANDIDATE SUBMISSION (CAND-152-02: MACRO COORDINATOR)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    macro_hook_code = '''def _apply_fixed_board_adaptation(obs, action):
    """Full-Game Macro Semantic Task Coordinator with 100% Critical Milestone Protection."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", [0]) or [0]
    shed = own_farm.get("inventory", {}) or {}
    hour = step % 24
    day = step // 24

    # PHASE A: Early Liquidity & Land 2 Expansion (Steps 74 - 170)
    if step == 75:
        copied["market"].append(["SELL", "MELON", 6])
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    if step == 152:
        copied["market"].append(["BUY_LAND"])

    # Protect Hands 0..3 (Critical Milestones: Pasture 2 @ 159, Cow Pickup @ 170)
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

    # PHASE B: Pre-Clearance Ripe Commodity Liquidation (Hour 23)
    if hour == 23 and step >= 200:
        straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
        milk_cnt = int(shed.get("MILK", 0) or 0)
        if straw_cnt >= 4:
            copied["market"].append(["SELL", "STRAWBERRY", straw_cnt])
        if milk_cnt >= 4:
            copied["market"].append(["SELL", "MILK", milk_cnt])

    # PHASE C: Terminal Feed Conservation (Steps 672 - 719)
    if step >= 672:
        # Filter out town wheat purchases if shed has sufficient feed reserve
        shed_wheat = int(shed.get("WHEAT", 0) or 0)
        if shed_wheat >= 12:
            copied["market"] = [m for m in copied["market"] if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, macro_hook_code, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0152", "candidate")
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
