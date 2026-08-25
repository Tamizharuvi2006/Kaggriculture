"""
Build APEX 4.0 Model A: 8-Cow Industrial Livestock Engine Candidate Submission
Modifies submission.py:
1. Implements Pasture 3 construction at Step 288 in NE quadrant.
2. Purchases 4 additional Cows at Step 312 and deploys them into Pasture 3.
3. Scales recurring milk production from 16 milk/day to 32 milk/day for Steps 316 to 720.
4. Preserves 100% critical milestone invariants for Pasture 1, Pasture 2, and initial herd.
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
    print("[APEX 4.0] BUILDING MODEL A: 8-COW INDUSTRIAL LIVESTOCK CANDIDATE")
    print("==========================================================================\n")
    
    base_sub_path = os.path.join(_PROJECT_ROOT, "submission.py")
    with open(base_sub_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    eight_cow_hook = '''def _apply_fixed_board_adaptation(obs, action):
    """APEX 4.0 Model A: 8-Cow Industrial Livestock Engine."""
    copied = _copy_action(action)
    step = int(_get(obs, "step", 0) or 0)
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied

    own_farm = farms[player]
    unlocked = own_farm.get("unlocked_quadrants", []) or []
    shed = own_farm.get("inventory", {}) or {}
    money = float(_get(own_farm, "money", 0.0) or 0.0)
    hands = copied.get("hands", [])
    hour = step % 24

    # 1. CAPITAL & REINVESTMENT SCALING
    # Step 75: Melon Liquidity Conversion
    if step == 75:
        melon_cnt = int(shed.get("MELON", 0) or 0)
        if melon_cnt >= 6:
            copied["market"].append(["SELL", "MELON", melon_cnt])
            copied["market"].append(["BUY_SEED", "STRAWBERRY", 6])

    # Step 152: Dynamic Land 2 Expansion
    if step == 152 and len(unlocked) == 1 and money >= 1000.0:
        copied["market"].append(["BUY_LAND"])

    # Step 156: Synchronized Initial Seed Purchase
    if step == 156:
        copied["market"].append(["BUY_SEED", "STRAWBERRY", 2])

    # Step 312: 8-Cow Herd Expansion Purchase (4 Extra Cows + Feed)
    if step == 312 and money >= 2500.0:
        copied["market"].append(["BUY_ANIMAL", "COW", 4])
        copied["market"].append(["BUY_PRODUCT", "WHEAT", 16])

    # Daily Feed Replenishment (Every Day at Hour 0 after Step 312)
    if hour == 0 and step >= 312 and step < 672:
        shed_wheat = int(shed.get("WHEAT", 0) or 0)
        if shed_wheat < 16 and money >= 500.0:
            copied["market"].append(["BUY_PRODUCT", "WHEAT", 12])

    # 2. WORKER ALLOCATION FOR 8-COW LIVESTOCK ENGINE
    # Step 288: Pasture 3 Construction in NE Quadrant (Workers #4 & #5)
    if 'NE' in unlocked and step == 288 and len(hands) >= 6:
        copied["hands"][4] = ["BUILD_PASTURE"]
        copied["hands"][5] = ["BUILD_PASTURE"]

    # Steps 313-316: Cow Deployment into Pasture 3 (Workers #4 & #5)
    if 'NE' in unlocked and len(hands) >= 6:
        if step == 313:
            copied["hands"][4] = ["PICKUP", "COW", 2]
            copied["hands"][5] = ["PICKUP", "COW", 2]
        elif step in (314, 315):
            copied["hands"][4] = ["EAST"]
            copied["hands"][5] = ["EAST"]

    # 3. HIGH-THROUGHPUT MILK CLEARANCE (Hour 23)
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
        if shed_wheat >= 16:
            copied["market"] = [m for m in copied["market"] if not (isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT")]

    return copied
'''
    
    pattern = r'def _apply_fixed_board_adaptation\(obs, action\):[\s\S]*?return copied\n'
    new_code = re.sub(pattern, eight_cow_hook, code)
    
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
