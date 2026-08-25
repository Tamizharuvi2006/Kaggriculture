"""
Build APEX 4.0 Research Candidate Submission
Modifies submission.py:
1. Injects the complete APEX 4.0 Closed-Loop System into submission.py.
Produces:
- apex_next/apex4/candidate/candidate_submission.py
"""
import os
import sys
import json
import hashlib
import re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def build_apex4_candidate():
    print("==========================================================================")
    print("[APEX 4.0] PHASE 15: BUILDING APEX 4.0 RESEARCH CANDIDATE SUBMISSION")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    apex4_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """APEX 4.0 Master Closed-Loop Policy Engine with 100% Critical Milestone Invariants."""
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

    # 1. CAPITAL & RESOURCE SYNCHRONIZATION
    # Step 75: Day 4 Melon Liquidity Conversion
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # Step 152: Dynamic Land 2 Expansion
    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    # Step 156: Synchronized Seed Purchase (Purchases 2 extra seeds for Worker #3)
    if step == 156:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # 2. CLOSED-LOOP WORKER ALLOCATION WITH PROTECTED MILESTONES
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

    # 3. PRE-CLEARANCE LIQUIDATION & TERMINAL LOGISTICS
    # Hour 23 Clearance Selling
    if hour == 23 and step >= 200:
        straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
        milk_cnt = int(shed.get("MILK", 0) or 0)
        if straw_cnt >= 4:
            copied["market"].append(["SELL", "STRAWBERRY", straw_cnt])
        if milk_cnt >= 4:
            copied["market"].append(["SELL", "MILK", milk_cnt])

    # Terminal Feed Conservation (Steps 672+)
    if step >= 672:
        shed_wheat = int(shed.get("WHEAT", 0) or 0)
        if shed_wheat >= 12:
            copied["market"] = [m for m in copied["market"] if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, apex4_hook, code)
    
    out_dir = os.path.join(_PROJECT_ROOT, "apex_next", "apex4", "candidate")
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
    build_apex4_candidate()
