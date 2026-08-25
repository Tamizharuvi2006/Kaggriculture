"""
Build APEX 4.0 2-Tile Dedicated Regional Allocation Candidate Submission
Modifies submission.py:
1. Implements observation-driven 2-tile NE regional farming (Tiles (3, 6) and (2, 6)) using Workers #4 and #5.
2. Preserves 100% critical infrastructure milestones.
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
    print("[APEX 4.0] BUILDING 2-TILE DEDICATED REGIONAL CANDIDATE SUBMISSION")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    two_tile_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """APEX 4.0 2-Tile Dedicated Regional Policy Engine (Tiles (3,6) & (2,6))."""
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

    # 1. CAPITAL & DYNAMIC SEED REPLENISHMENT
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    if step == 156:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 4])

    if 'NE' in unlocked and step >= 180 and (step % 24 == 0) and int(shed.get("STRAWBERRY", 0) or 0) <= 1 and money >= 300.0:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # 2. WORKER #4 DEDICATED TO NE TILE (3, 6)
    if 'NE' in unlocked and step >= 172 and len(hands) >= 5:
        t36 = tiles[3][6] if len(tiles) > 3 and len(tiles[3]) > 6 else None
        if step in (172, 173, 174):
            copied["hands"][4] = ["EAST"]
        elif t36 is None:
            copied["hands"][4] = ["TILL"]
        elif isinstance(t36, dict):
            if t36.get("yield_units", 0) > 0:
                copied["hands"][4] = ["HARVEST"]
            elif not t36.get("watered_today", False):
                copied["hands"][4] = ["WATER"]
            elif t36.get("kind") == "TILLED" and int(shed.get("STRAWBERRY", 0) or 0) > 0:
                copied["hands"][4] = ["PLANT", "STRAWBERRY"]

    # 3. WORKER #5 DEDICATED TO NE TILE (2, 6)
    if 'NE' in unlocked and step >= 173 and len(hands) >= 6:
        t26 = tiles[2][6] if len(tiles) > 2 and len(tiles[2]) > 6 else None
        if step in (173, 174, 175):
            copied["hands"][5] = ["EAST"]
        elif t26 is None:
            copied["hands"][5] = ["TILL"]
        elif isinstance(t26, dict):
            if t26.get("yield_units", 0) > 0:
                copied["hands"][5] = ["HARVEST"]
            elif not t26.get("watered_today", False):
                copied["hands"][5] = ["WATER"]
            elif t26.get("kind") == "TILLED" and int(shed.get("STRAWBERRY", 0) or 0) > 0:
                copied["hands"][5] = ["PLANT", "STRAWBERRY"]

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
    new_code = re.sub(pattern, two_tile_hook, code)
    
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
