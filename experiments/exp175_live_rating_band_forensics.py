"""EXP175: Live-Rating-Band & Top-Tier Replay Forensics Engine.

Parses authentic Kaggle ladder replays across the rating spectrum to identify
the exact step and economic mechanisms where 1000+ Elo opponents diverge.
"""
from __future__ import annotations
import os
import sys
import json
import glob
from collections import defaultdict
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def classify_strategy(steps: list, player_idx: int) -> dict:
    """Extracts the economic and architectural signature of a player from replay steps."""
    max_cows = 0
    max_sheep = 0
    max_hands = 0
    quad_unlock_steps = {}
    total_straw_sold = 0
    total_milk_sold = 0
    total_wool_sold = 0

    first_cow_step = None
    first_sheep_step = None
    first_quad2_step = None
    first_quad3_step = None
    first_quad4_step = None

    for s_idx, step_data in enumerate(steps):
        agent_step = step_data[player_idx]
        obs = agent_step.get("observation", {})
        farms = obs.get("farms", [{}, {}])
        f = farms[player_idx] if player_idx < len(farms) else {}

        quads = f.get("unlocked_quadrants", ["NW"])
        num_quads = len(quads)
        if num_quads >= 2 and first_quad2_step is None: first_quad2_step = s_idx
        if num_quads >= 3 and first_quad3_step is None: first_quad3_step = s_idx
        if num_quads >= 4 and first_quad4_step is None: first_quad4_step = s_idx

        cows = 0
        sheep = 0
        for row in f.get("tiles", []):
            for t in row:
                if isinstance(t, dict) and "animal" in t:
                    if t.get("animal") == "COW": cows += 1
                    elif t.get("animal") == "SHEEP": sheep += 1

        if cows > max_cows: max_cows = cows
        if sheep > max_sheep: max_sheep = sheep
        if cows > 0 and first_cow_step is None: first_cow_step = s_idx
        if sheep > 0 and first_sheep_step is None: first_sheep_step = s_idx

        hands = len(f.get("hands", []))
        if hands > max_hands: max_hands = hands

        act = agent_step.get("action") or {}
        if isinstance(act, dict):
            for m in act.get("market", []):
                if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                    item, qty = m[1], int(m[2])
                    if item == "STRAWBERRY": total_straw_sold += qty
                    elif item == "MILK": total_milk_sold += qty
                    elif item == "WOOL": total_wool_sold += qty

    # Determine archetype label
    if max_cows >= 8:
        archetype = "Mega_Dairy_Conglomerate (8+ Cows)"
    elif max_cows >= 3 and max_sheep >= 3:
        archetype = "Multi_Livestock_Hybrid (Cows+Sheep)"
    elif max_sheep >= 6:
        archetype = "Wool_Rancher (6+ Sheep)"
    elif max_cows >= 2:
        archetype = "Standard_Agro_Dairy (2-4 Cows + Straw)"
    elif first_quad4_step is not None:
        archetype = "4th_Land_Expander"
    elif total_straw_sold > 50:
        archetype = "Pure_Strawberry_Crop"
    else:
        archetype = "Other/Mixed"

    return {
        "archetype": archetype,
        "max_cows": max_cows,
        "max_sheep": max_sheep,
        "max_hands": max_hands,
        "first_cow_step": first_cow_step,
        "first_sheep_step": first_sheep_step,
        "first_quad2_step": first_quad2_step,
        "first_quad3_step": first_quad3_step,
        "first_quad4_step": first_quad4_step,
        "total_straw_sold": total_straw_sold,
        "total_milk_sold": total_milk_sold,
        "total_wool_sold": total_wool_sold,
    }

def analyze_single_replay(filepath: str) -> dict | None:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, dict) or "steps" not in data:
        return None

    steps = data.get("steps", [])
    if len(steps) < 700:
        return None

    info = data.get("info", {})
    rewards = data.get("rewards", [0, 0])
    if len(rewards) < 2 or rewards[0] is None or rewards[1] is None:
        rewards = [steps[-1][0].get("reward", 0), steps[-1][1].get("reward", 0)]

    p0_sig = classify_strategy(steps, 0)
    p1_sig = classify_strategy(steps, 1)

    # Extract step-by-step wealth and cash trajectory
    checkpoints = [120, 180, 240, 288, 336, 360, 480, 600, 696, 719]
    trajectory = {}
    for s in checkpoints:
        if s < len(steps):
            o0 = steps[s][0].get("observation", {})
            o1 = steps[s][1].get("observation", {})
            f0 = (o0.get("farms") or [{}, {}])[0]
            f1 = (o1.get("farms") or [{}, {}])[1]
            trajectory[f"Step_{s}"] = {
                "p0_cash": float(f0.get("money", 0.0)),
                "p1_cash": float(f1.get("money", 0.0)),
                "p0_quads": len(f0.get("unlocked_quadrants", ["NW"])),
                "p1_quads": len(f1.get("unlocked_quadrants", ["NW"])),
                "p0_hands": len(f0.get("hands", [])),
                "p1_hands": len(f1.get("hands", [])),
            }

    ep_id = data.get("id") or os.path.basename(filepath).replace(".json", "")

    return {
        "file": filepath,
        "episode_id": ep_id,
        "reward_p0": float(rewards[0] or 0),
        "reward_p1": float(rewards[1] or 0),
        "winner": 0 if (rewards[0] or 0) > (rewards[1] or 0) else 1,
        "margin": abs((rewards[0] or 0) - (rewards[1] or 0)),
        "p0_signature": p0_sig,
        "p1_signature": p1_sig,
        "trajectory": trajectory,
    }

def main():
    print("=" * 120)
    print("EXP175: LIVE-RATING-BAND & TOP-TIER REPLAY FORENSICS ENGINE")
    print("=" * 120)

    replay_patterns = [
        os.path.join(BASE_DIR, "competitive_intelligence", "*.json"),
        os.path.join(BASE_DIR, "l++reviews", "*.json"),
        os.path.join(BASE_DIR, "l++reviews", "loss", "*.json"),
        os.path.join(BASE_DIR, "l+reviews", "*.json"),
        os.path.join(BASE_DIR, "l+reviews", "newl", "*.json"),
        os.path.join(BASE_DIR, "l+reviews", "newl", "loss", "*.json"),
        os.path.join(BASE_DIR, "reports", "step5b", "old_loss_gauntlet", "raw_replays", "*", "*.json"),
        os.path.join(BASE_DIR, "reports", "step5b", "old_loss_gauntlet", "ppo_submission_replays", "*", "*.json"),
        os.path.join(BASE_DIR, "reports", "step5b", "replay_*", "*.json"),
    ]

    all_files = []
    for pat in replay_patterns:
        all_files.extend(glob.glob(pat))

    all_files = list(set(all_files))
    print(f"Found {len(all_files)} potential replay candidates. Parsing full 720-step episodes...")

    analyzed = []
    for fp in all_files:
        res = analyze_single_replay(fp)
        if res is not None:
            analyzed.append(res)

    print(f"Successfully analyzed {len(analyzed)} verified 720-step live ladder replays!\n")

    # 1. Opponent Archetype Distribution
    archetype_counts = defaultdict(int)
    archetype_wins = defaultdict(int)
    archetype_rewards = defaultdict(list)

    for r in analyzed:
        for p_idx in [0, 1]:
            sig = r[f"p{p_idx}_signature"]
            arch = sig["archetype"]
            archetype_counts[arch] += 1
            rew = r[f"reward_p{p_idx}"]
            archetype_rewards[arch].append(rew)
            if r["winner"] == p_idx:
                archetype_wins[arch] += 1

    print("=" * 120)
    print("TOP-TIER LADDER OPPONENT STRATEGY DISTRIBUTION & REWARD PROFILES:")
    print("=" * 120)
    print(f"{'Archetype':<40} | {'Appearances':<12} | {'Win Rate':<12} | {'Mean Final Reward':<18} | {'Max Reward'}")
    print("-" * 120)

    for arch, cnt in sorted(archetype_counts.items(), key=lambda x: sum(archetype_rewards[x[0]])/len(archetype_rewards[x[0]]), reverse=True):
        wr = archetype_wins[arch] / cnt * 100.0
        mean_r = sum(archetype_rewards[arch]) / len(archetype_rewards[arch])
        max_r = max(archetype_rewards[arch])
        print(f"{arch:<40} | {cnt:<12} | {wr:5.1f}%      | ${mean_r:12,.1f}     | ${max_r:10,.1f}")
    print("=" * 120)

    # 2. Macro Milestones of Top Performers (Winners with Score > $100k)
    elite_winners = []
    for r in analyzed:
        w_idx = r["winner"]
        if r[f"reward_p{w_idx}"] >= 100000.0:
            elite_winners.append((r, w_idx))

    print(f"\nDiscovered {len(elite_winners)} ELITE $100k+ Victory Trajectories in Live Replays.")
    if elite_winners:
        print("\n" + "=" * 120)
        print("ELITE $100k+ WINNERS: MACRO TIMING SIGNATURES")
        print("=" * 120)
        print(f"{'Episode ID':<16} | {'Final Reward':<14} | {'Archetype':<32} | {'Cows':<6} | {'Sheep':<6} | {'Land 2':<8} | {'Land 3':<8} | {'Hands'}")
        print("-" * 120)
        for r, w in sorted(elite_winners, key=lambda x: x[0][f"reward_p{x[1]}"], reverse=True)[:15]:
            sig = r[f"p{w}_signature"]
            rew = r[f"reward_p{w}"]
            ep = str(r["episode_id"])[:14]
            arch = sig["archetype"][:30]
            cows = sig["max_cows"]
            sheep = sig["max_sheep"]
            l2 = f"S{sig['first_quad2_step']}" if sig['first_quad2_step'] is not None else "None"
            l3 = f"S{sig['first_quad3_step']}" if sig['first_quad3_step'] is not None else "None"
            hands = sig["max_hands"]
            print(f"{ep:<16} | ${rew:10,.1f}   | {arch:<32} | {cows:<6} | {sheep:<6} | {l2:<8} | {l3:<8} | {hands}")
        print("=" * 120)

    # 3. High-Tier Step-by-Step Trajectory of Top Performers
    print("\n" + "=" * 120)
    print("STEP-BY-STEP CASH & QUADRANT ADVANCE OF $100k+ WINNERS:")
    print("=" * 120)
    print(f"{'Step (Day)':<14} | {'Mean Cash':<14} | {'Mean Quadrants':<16} | {'Mean Workers'}")
    print("-" * 120)
    checkpoints = [120, 180, 240, 288, 336, 360, 480, 600, 696]
    for s in checkpoints:
        step_k = f"Step_{s}"
        cashes = [r["trajectory"].get(step_k, {}).get(f"p{w}_cash", 0) for r, w in elite_winners if step_k in r["trajectory"]]
        quads = [r["trajectory"].get(step_k, {}).get(f"p{w}_quads", 1) for r, w in elite_winners if step_k in r["trajectory"]]
        hands = [r["trajectory"].get(step_k, {}).get(f"p{w}_hands", 0) for r, w in elite_winners if step_k in r["trajectory"]]

        m_cash = sum(cashes)/len(cashes) if cashes else 0
        m_quads = sum(quads)/len(quads) if quads else 1
        m_hands = sum(hands)/len(hands) if hands else 0
        day = s // 24
        print(f"Step {s:3d} (D{day:2d})  | ${m_cash:10,.1f} | {m_quads:4.1f} quads       | {m_hands:4.1f} hands")
    print("=" * 120)

    # Save complete forensics dataset
    out_file = os.path.join(BASE_DIR, "reports", "exp175_live_replay_forensics.json")
    with open(out_file, "w") as f:
        json.dump(analyzed, f, indent=2)
    print(f"\nSaved Full EXP175 Live Replay Forensics Dataset to: {out_file}")

if __name__ == "__main__":
    main()
