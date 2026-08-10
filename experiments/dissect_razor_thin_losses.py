"""Dissect Razor-Thin Losses (-$200 to -$2.5k) for Candidate L+ Forensic Audit.
"""

import sys
import os
import json
import glob

# Force UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGET_REPLAYS = [
    os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "91292018.json"),
    os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "91287496.json"),
    os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "91286593.json"),
]

def analyze_replay(fpath):
    fname = os.path.basename(fpath)
    print(f"\n====================================================")
    print(f"🔬 FORENSIC DISSECTION OF NARROW LOSS: {fname}")
    print(f"====================================================")
    
    if not os.path.exists(fpath):
        print(f"File not found: {fpath}")
        return

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    steps = data.get("steps", [])
    if not steps:
        print("No steps found in replay.")
        return

    # Determine index of L+ vs Opponent
    # In reviews loss folder, L+ is usually the player with lower final money or index 0/1
    last_step = steps[-1]
    p0_final = last_step[0]["observation"]["farms"][0]["money"]
    p1_final = last_step[1]["observation"]["farms"][1]["money"]
    
    # We know in loss folder, L+ lost.
    if p0_final <= p1_final:
        lplus_idx = 0
        opp_idx = 1
    else:
        lplus_idx = 1
        opp_idx = 0

    lplus_final = last_step[lplus_idx]["observation"]["farms"][lplus_idx]["money"]
    opp_final = last_step[opp_idx]["observation"]["farms"][opp_idx]["money"]
    delta = lplus_final - opp_final
    
    print(f"  Final Wealth: Candidate L+ = ${lplus_final:,.2f} | Opponent = ${opp_final:,.2f}")
    print(f"  Net Victory Margin: ${delta:+,.2f}")
    
    print("\n--- DAY-BY-DAY WEALTH & CASH TRAJECTORY ---")
    print(f"{'Day':^5} | {'L+ Money':^12} | {'Opp Money':^12} | {'Delta ($)':^12} | {'Leader':^10}")
    print("-" * 60)

    # Sample steps per day (~24 steps per day)
    day_steps = []
    for step_num, step in enumerate(steps):
        day = step[0]["observation"].get("step", step_num) // 24
        # Store last step of each day
        if step_num == len(steps) - 1 or (step_num + 1) % 24 == 0:
            p_lplus = step[lplus_idx]["observation"]["farms"][lplus_idx]["money"]
            p_opp = step[opp_idx]["observation"]["farms"][opp_idx]["money"]
            day_steps.append((day, p_lplus, p_opp))

    # Print summary every 2 days
    for day, p_lplus, p_opp in day_steps:
        d = p_lplus - p_opp
        leader = "L+" if d >= 0 else "Opponent"
        if day in [1, 5, 10, 15, 20, 25, 28, 29, 30] or day == day_steps[-1][0]:
            print(f"Day {day:2d} | ${p_lplus:10,.2f} | ${p_opp:10,.2f} | ${d:+10,.2f} | {leader}")

    # Inspect End-Game Inventory & Unsold Assets on Day 28-30
    print("\n--- END-GAME ASSET & UNREALIZED WEALTH BREAKDOWN (DAY 28-30) ---")
    last_farm_lplus = last_step[lplus_idx]["observation"]["farms"][lplus_idx]
    last_farm_opp = last_step[opp_idx]["observation"]["farms"][opp_idx]

    lplus_inventory = last_farm_lplus.get("inventory", {})
    opp_inventory = last_farm_opp.get("inventory", {})

    print(f"  Candidate L+ Unsold Inventory: {lplus_inventory}")
    print(f"  Opponent Unsold Inventory:     {opp_inventory}")

    # Count animals / structures
    lplus_cows = len(last_farm_lplus.get("cows", []))
    opp_cows = len(last_farm_opp.get("cows", []))
    lplus_sheep = len(last_farm_lplus.get("sheep", []))
    opp_sheep = len(last_farm_opp.get("sheep", []))

    print(f"  Candidate L+ Livestock: {lplus_cows} Cows, {lplus_sheep} Sheep")
    print(f"  Opponent Livestock:     {opp_cows} Cows, {opp_sheep} Sheep")

    # Diagnosis hypothesis
    print("\n--- SURGICAL FORENSIC DIAGNOSIS ---")
    if abs(delta) < 500:
        print(f"  [CRITICAL FINDING]: Loss margin is extremely tiny (${abs(delta):.2f}). A single extra market sale or 1 fewer transit turn on Day 29 would reverse this result into a WIN!")
    elif abs(delta) < 2500:
        print(f"  [SURGICAL FINDING]: Narrow loss (${abs(delta):.2f}). Caused by minor end-game timing gap or un-harvested crop/milk cycles on Day 28-30.")

def main():
    print("====================================================")
    print("KAGGRICULTURE SURGICAL FORENSICS: NARROW LOSSES")
    print("====================================================")
    for fpath in TARGET_REPLAYS:
        analyze_replay(fpath)

if __name__ == "__main__":
    main()
