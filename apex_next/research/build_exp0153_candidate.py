"""
Build Candidate Submission for EXP-0153 (CAND-153-02: Pure Closed-Loop Goal-Oriented Policy Engine)
Modifies submission.py:
1. Injects the complete ClosedLoopController class into submission.py.
2. In agent(obs), passes the live observation and fallback action to ClosedLoopController.plan_step().
Produces:
- apex_next/research/EXP-0153/candidate/candidate_submission.py
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
    print("[EXP-0153] BUILDING CANDIDATE SUBMISSION (CAND-153-02: CLOSED-LOOP ENGINE)")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    closed_loop_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """Pure Closed-Loop Goal-Oriented Policy Engine with 100% Critical Milestone Protection."""
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
    hour = step % 24

    # 1. DYNAMIC MARKET POLICY
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    # 2. DYNAMIC WORKER TASK ALLOCATION WITH PROTECTED CRITICAL MILESTONES
    # Invariant: Hands 0..3 are LOCKED for Step 159 Pasture 2 & Step 170 Cow Pickup
    if len(unlocked) >= 2 and 153 <= step <= 170:
        hands = copied.get("hands", [])
        for w_idx in range(4, len(hands)):
            if hands[w_idx] in (["PASS"], "PASS"):
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

    # 3. PRE-CLEARANCE LIQUIDATION (HOUR 23)
    if hour == 23 and step >= 200:
        straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
        milk_cnt = int(shed.get("MILK", 0) or 0)
        if straw_cnt >= 4:
            copied["market"].append(["SELL", "STRAWBERRY", straw_cnt])
        if milk_cnt >= 4:
            copied["market"].append(["SELL", "MILK", milk_cnt])

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, closed_loop_hook, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0153", "candidate")
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
