"""Builder for Candidate L+ EG (End-Game Dump Guard ONLY).
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FILE = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
DST_FILE = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus_eg.py")

ENDGAME_DUMP_GUARD_CODE = '''

def _apply_endgame_dump_guard(obs, action):
    try:
        step = int(_get(obs, "step", 0))
        if step < 672:
            return action

        player = int(_get(obs, "player", 0))
        farms = _get(obs, "farms", []) or []
        if len(farms) > player:
            my_farm = farms[player]
            inv = _get(my_farm, "inventory", {}) or {}
            
            orders = list(action.get("market", []))
            existing_sells = set(ord[1] for ord in orders if len(ord) >= 2 and ord[0] == "SELL")
            
            sellable_items = ["WHEAT", "STRAWBERRY", "MELON", "MILK", "WOOL", "CARROT", "TOMATO", "FERTILIZER"]
            for item in sellable_items:
                qty = int(inv.get(item, 0))
                if qty > 0 and item not in existing_sells and len(orders) < 10:
                    orders.append(["SELL", item, qty])
                    
            action["market"] = orders[:10]

        if step >= 705 and "hands" in action:
            hands = action.get("hands", [])
            new_hands = []
            for h in hands:
                if isinstance(h, list) and len(h) == 1 and h[0] in ("NORTH", "SOUTH", "EAST", "WEST") and step >= 712:
                    new_hands.append(["PASS"])
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

    # Insert helper function before agent(obs)
    agent_pos = content.rfind("def agent(obs):")
    if agent_pos == -1:
        print("Error: def agent(obs) not found!")
        sys.exit(1)

    new_content = content[:agent_pos] + ENDGAME_DUMP_GUARD_CODE + "\n\n" + content[agent_pos:]

    # Wrap the return value of agent(obs) with _apply_endgame_dump_guard(obs, result)
    old_return = "return _apply_fixed_board_adaptation(obs, overlaid)"
    new_return = "return _apply_endgame_dump_guard(obs, _apply_fixed_board_adaptation(obs, overlaid))"

    if old_return in new_content:
        new_content = new_content.replace(old_return, new_return)
        print("Successfully injected _apply_endgame_dump_guard into agent(obs) return path!")
    else:
        print("Warning: old_return string not found directly.")

    print(f"Writing Candidate L+ EG to {DST_FILE}...")
    with open(DST_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Successfully generated Candidate L+ EG ({os.path.getsize(DST_FILE)} bytes)!")

if __name__ == "__main__":
    build()
