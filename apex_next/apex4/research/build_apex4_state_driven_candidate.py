"""
Build APEX 4.0 Observation-Driven Regional Candidate Submission
Modifies submission.py:
1. Injects plan_state_driven_regional_action into _apply_fixed_board_adaptation().
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


def build_candidate():
    print("==========================================================================")
    print("[APEX 4.0] BUILDING OBSERVATION-DRIVEN REGIONAL CANDIDATE SUBMISSION")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    state_driven_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """APEX 4.0 Observation-Driven Regional Controller with 100% Milestone Invariants."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", []) or []
    tiles = own_farm.get("tiles", []) or []
    shed = own_farm.get("inventory", {}) or {}
    money = float(_get(own_farm, "money", 0.0) or 0.0)
    hands = copied.get("hands", [])
    hour = step % 24

    # 1. CAPITAL & RESOURCE SYNCHRONIZATION
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    if step == 156:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    if 'NE' in unlocked and step >= 180 and (step % 24 == 0) and int(shed.get("STRAWBERRY", 0) or 0) == 0 and money >= 300.0:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # 2. WORKER #3 INITIAL NE CULTIVATION (Steps 172 to 180)
    if 'NE' in unlocked and 172 <= step <= 180 and len(hands) >= 4:
        t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
        if step in (172, 173, 174):
            copied["hands"][3] = ["EAST"]
        elif step == 175:
            if t26 is None:
                copied["hands"][3] = ["TILL"]
            else:
                copied["hands"][3] = ["PASS"]
        elif step == 176:
            straw_seeds = int(shed.get("STRAWBERRY", 0) or 0)
            if straw_seeds > 0 or t26 is not None:
                copied["hands"][3] = ["PLANT", "STRAWBERRY"]
            else:
                copied["hands"][3] = ["PASS"]
        elif step == 177:
            copied["hands"][3] = ["WATER"]
        elif step in (178, 179):
            copied["hands"][3] = ["WEST"]
        elif step == 180:
            copied["hands"][3] = ["PASS"]

    # 3. WORKER #4 OBSERVATION-DRIVEN REGIONAL MAINTENANCE (Steps 185 to 719)
    if 'NE' in unlocked and step >= 185 and len(hands) >= 5:
        t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
        if t26 is not None and isinstance(t26, dict):
            if t26.get("yield_units", 0) > 0:
                copied["hands"][4] = ["HARVEST"]
            elif not t26.get("watered_today", False):
                copied["hands"][4] = ["WATER"]
            elif t26.get("kind") == "TILLED" and int(shed.get("STRAWBERRY", 0) or 0) > 0:
                copied["hands"][4] = ["PLANT", "STRAWBERRY"]

    # 4. PRE-CLEARANCE LIQUIDATION & TERMINAL LOGISTICS
    if hour == 23 and step >= 200:
        straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
        milk_cnt = int(shed.get("MILK", 0) or 0)
        if straw_cnt >= 4:
            copied["market"].append(["SELL", "STRAWBERRY", straw_cnt])
        if milk_cnt >= 4:
            copied["market"].append(["SELL", "MILK", milk_cnt])

    if step >= 672:
        shed_wheat = int(shed.get("WHEAT", 0) or 0)
        if shed_wheat >= 12:
            copied["market"] = [m for m in copied["market"] if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, state_driven_hook, code)
    
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
    build_candidate()
