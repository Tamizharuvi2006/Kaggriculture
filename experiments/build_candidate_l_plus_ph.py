"""Builder for Candidate L+ PH (Pasture Harvest Priority ONLY).
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FILE = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
DST_FILE = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus_ph.py")

PASTURE_HARVEST_PRIORITY_CODE = '''

def _apply_pasture_harvest_priority(obs, action):
    try:
        step = int(_get(obs, "step", 0))
        if step < 672:
            return action

        player = int(_get(obs, "player", 0))
        farms = _get(obs, "farms", []) or []
        if len(farms) <= player:
            return action

        my_farm = farms[player]
        tiles = [tile for row in (_get(my_farm, "tiles", []) or []) for tile in row if isinstance(tile, dict)]
        
        # Check if pasture crops (STRAWBERRY, TOMATO) are ready to harvest
        pasture_ready = any(
            t.get("kind") == "PLANT" and t.get("crop") in ("STRAWBERRY", "TOMATO") and t.get("yield", 0) > 0
            for t in tiles
        )

        if pasture_ready and "hands" in action:
            hands = action.get("hands", [])
            new_hands = []
            for h in hands:
                # If hand is performing a PLANT action on Day 28-30, replace with HARVEST if on a crop tile
                if isinstance(h, list) and len(h) >= 1 and h[0] == "PLANT":
                    new_hands.append(["HARVEST"])
                else:
                    new_hands.append(h)
            action["hands"] = new_hands

        return action
    except Exception:
        return action
'''

def build():
    print(f"Reading base L+ from {SRC_FILE}...")
    with open(SRC_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    agent_pos = content.rfind("def agent(obs):")
    if agent_pos == -1:
        print("Error: def agent(obs) not found!")
        sys.exit(1)

    new_content = content[:agent_pos] + PASTURE_HARVEST_PRIORITY_CODE + "\n\n" + content[agent_pos:]

    old_return = "return _apply_fixed_board_adaptation(obs, overlaid)"
    new_return = "return _apply_pasture_harvest_priority(obs, _apply_fixed_board_adaptation(obs, overlaid))"

    if old_return in new_content:
        new_content = new_content.replace(old_return, new_return)
        print("Successfully injected _apply_pasture_harvest_priority into agent(obs) return path!")
    else:
        print("Warning: old_return string not found directly.")

    print(f"Writing Candidate L+ PH to {DST_FILE}...")
    with open(DST_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Successfully generated Candidate L+ PH ({os.path.getsize(DST_FILE)} bytes)!")

if __name__ == "__main__":
    build()
