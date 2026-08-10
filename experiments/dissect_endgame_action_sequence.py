"""Dissect End-Game Worker Actions (Steps 650-720, Days 27-30) for Narrow Losses.
"""

import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    ("91292018.json", os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "91292018.json")),
    ("91287496.json", os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "91287496.json")),
]

def dissect_endgame_actions(name, fpath):
    print(f"\n====================================================")
    print(f"🕵️ END-GAME ACTION DISSECTION (STEPS 600-720): {name}")
    print(f"====================================================")
    
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    steps = data.get("steps", [])
    last_step = steps[-1]
    p0_final = last_step[0]["observation"]["farms"][0]["money"]
    p1_final = last_step[1]["observation"]["farms"][1]["money"]

    if p0_final <= p1_final:
        lplus_idx, opp_idx = 0, 1
    else:
        lplus_idx, opp_idx = 1, 0

    print(f"  Player Indices -> L+: P{lplus_idx} | Opponent: P{opp_idx}")

    # Inspect last 120 steps (Steps 600 to 720)
    endgame_steps = steps[600:]
    
    # Track inventory drops, sales, crops ready, transit turns
    lplus_sales_endgame = 0
    opp_sales_endgame = 0

    for s_idx, step in enumerate(endgame_steps, start=600):
        obs_lplus = step[lplus_idx]["observation"]["farms"][lplus_idx]
        obs_opp = step[opp_idx]["observation"]["farms"][opp_idx]
        
        m_lplus = obs_lplus["money"]
        m_opp = obs_opp["money"]

        # Check if action was taken in step
        act_lplus = step[lplus_idx].get("action", [])
        act_opp = step[opp_idx].get("action", [])

        # Print snapshot when money changes
        if s_idx > 600:
            prev_lplus = endgame_steps[s_idx - 601][lplus_idx]["observation"]["farms"][lplus_idx]["money"]
            prev_opp = endgame_steps[s_idx - 601][opp_idx]["observation"]["farms"][opp_idx]["money"]

            if m_lplus != prev_lplus or m_opp != prev_opp:
                d_l = m_lplus - prev_lplus
                d_o = m_opp - prev_opp
                day = s_idx // 24
                hour = s_idx % 24
                print(f"  Step {s_idx:3d} (Day {day:2d}, Hr {hour:2d}) | L+ Money: ${m_lplus:9,.2f} ({d_l:+8,.2f}) | Opp Money: ${m_opp:9,.2f} ({d_o:+8,.2f}) | Margin: ${m_lplus - m_opp:+8,.2f}")
                if d_l != 0:
                    print(f"    -> L+ Action: {act_lplus}")
                if d_o != 0:
                    print(f"    -> Opp Action: {act_opp}")

def main():
    for name, fpath in TARGETS:
        dissect_endgame_actions(name, fpath)

if __name__ == "__main__":
    main()
