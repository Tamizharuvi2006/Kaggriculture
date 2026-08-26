"""EXP087: Real Live Defeat Deep Forensic Telemetry Inspector.

Parses the actual JSON replay logs of the large-deficit live defeats:
- Episode 99924838 (-$31,036: D.1 $42,227 vs Opp $73,263, Seed 1599299971)
- Episode 99915508 (-$29,289: D.1 $72,745 vs Opp $102,034, Seed 1487822928)
- Episode 99869827 (-$23,411: D.1 $68,849 vs Opp $92,260, Seed 1259752816)

Decomposes the real live match replay:
1. Exact cash trajectory for both players at each step (0 to 720)
2. Land purchases (which quadrants did D.1 buy vs Opponent?)
3. Cow purchases (did Opponent buy cows? How many?)
4. Worker count & hiring timeline
5. Seed purchases (what seeds did Opponent buy vs D.1?)
6. Market sell volume & timing
"""
from __future__ import annotations
import sys
import os
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

EPISODES = [99924838, 99915508, 99869827]

def inspect_episode(ep_id: int):
    path = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches", f"episode_{ep_id}.json")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        ep_data = json.load(f)

    steps = ep_data.get("steps", [])
    print("=" * 90)
    print(f"REAL LIVE MATCH DECOMPOSITION: Episode {ep_id}")
    print(f"Total Steps Logged: {len(steps)}")
    
    # Metadata inspection
    agents = ep_data.get("agents", [])
    print(f"Agents: {agents}")
    
    # Track actions and state across steps
    p0_rewards = []
    p1_rewards = []
    p0_cash = []
    p1_cash = []
    
    p0_actions = []
    p1_actions = []

    for idx, step_record in enumerate(steps):
        # step_record is a list of agent step dicts: [ {action, reward, observation, ...}, {action, reward, ...} ]
        if len(step_record) >= 2:
            s0 = step_record[0]
            s1 = step_record[1]
            p0_rewards.append(s0.get("reward", 0.0))
            p1_rewards.append(s1.get("reward", 0.0))
            p0_actions.append(s0.get("action"))
            p1_actions.append(s1.get("action"))

            obs0 = s0.get("observation", {})
            if isinstance(obs0, dict):
                farms = obs0.get("farms", [])
                if len(farms) >= 2:
                    p0_cash.append(farms[0].get("money", 0.0))
                    p1_cash.append(farms[1].get("money", 0.0))

    final_s0 = steps[-1][0] if steps else {}
    final_s1 = steps[-1][1] if steps else {}
    print(f"Final Reported Rewards in JSON: P0: ${final_s0.get('reward')}, P1: ${final_s1.get('reward')}")

    # Inspect key checkpoints
    checkpoints = [24, 72, 192, 360, 480, 600, 624, 696, 719]
    print("\nStep-by-Step Cash Trajectory in Real Kaggle Match:")
    print(f"{'Step':<8} | {'P0 Cash ($)':>14} | {'P1 Cash ($)':>14} | {'P0 Action Type':<25} | {'P1 Action Type'}")
    print("-" * 90)
    for cp in checkpoints:
        if cp < len(steps):
            c0 = p0_cash[cp] if cp < len(p0_cash) else 0.0
            c1 = p1_cash[cp] if cp < len(p1_cash) else 0.0
            act0 = p0_actions[cp]
            act1 = p1_actions[cp]
            act0_str = str(list(act0.keys()) if isinstance(act0, dict) else act0)[:25]
            act1_str = str(list(act1.keys()) if isinstance(act1, dict) else act1)[:25]
            print(f"Step {cp:<3} | ${c0:>13,.0f} | ${c1:>13,.0f} | {act0_str:<25} | {act1_str}")

    # Inspect what P0 and P1 bought throughout the whole game
    p0_all_market = [s.get("action", {}).get("market", []) for s in [step[0] for step in steps] if isinstance(s.get("action"), dict)]
    p1_all_market = [s.get("action", {}).get("market", []) for s in [step[1] for step in steps] if isinstance(s.get("action"), dict)]

    p0_buys = {}
    p1_buys = {}
    p0_sells = {}
    p1_sells = {}

    for orders in p0_all_market:
        for o in orders:
            if len(o) >= 3:
                if o[0] == "BUY":
                    p0_buys[o[1]] = p0_buys.get(o[1], 0) + o[2]
                elif o[0] == "SELL":
                    p0_sells[o[1]] = p0_sells.get(o[1], 0) + o[2]

    for orders in p1_all_market:
        for o in orders:
            if len(o) >= 3:
                if o[0] == "BUY":
                    p1_buys[o[1]] = p1_buys.get(o[1], 0) + o[2]
                elif o[0] == "SELL":
                    p1_sells[o[1]] = p1_sells.get(o[1], 0) + o[2]

    print("\nCumulative Market BUYS across 720 steps:")
    print(f"  • P0 Buys: {p0_buys}")
    print(f"  • P1 Buys: {p1_buys}")

    print("\nCumulative Market SELLS across 720 steps:")
    print(f"  • P0 Sells: {p0_sells}")
    print(f"  • P1 Sells: {p1_sells}")
    print("=" * 90)

if __name__ == "__main__":
    for ep in EPISODES:
        inspect_episode(ep)
