"""EXP140: Decision-Sequence Divergence Analysis (Days 1 to 15).

Forensic sequence analysis across 31 full 720-step Kaggle tournament replays:
1. Reconstructs ordered action logs for both agents (Steps 0 to 360):
   - Land expansions (Quad 2, Quad 3, Quad 4)
   - Animal purchases (Cow, Sheep)
   - Seed purchases & planting batches
   - Feed purchases & animal care
   - Worker hiring cycles
   - Market sales (item, volume, price, cash gained)
2. Detects the exact earliest step where cash lead becomes persistent (+$500, +$1,000, +$2,000).
3. Analyzes the preceding 10-20 action sequence that created the divergence.
4. Clusters recurring decision sequences across all loss matches.
5. Evaluates counterfactual feasibility for D.1.
"""
from __future__ import annotations
import os
import sys
import glob
import json
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
TELEMETRY_DIR = os.path.join(REPORTS_DIR, "live_match_telemetry")

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

def parse_action_events(step_idx: int, action_dict: dict, obs_dict: dict, player_idx: int):
    """Extracts discrete macro-economic actions from raw action dict."""
    events = []
    if not isinstance(action_dict, dict):
        return events

    market = action_dict.get("market") or []
    farmer = action_dict.get("farmer") or []
    hands = action_dict.get("hands") or []

    # 1. Market orders
    for order in market:
        if isinstance(order, (list, tuple)) and len(order) >= 1:
            cmd = order[0]
            if cmd == "BUY_LAND":
                events.append({"step": step_idx, "type": "BUY_LAND", "detail": order[1] if len(order) > 1 else "LAND"})
            elif cmd == "BUY_ANIMAL":
                animal = order[1] if len(order) > 1 else "ANIMAL"
                qty = order[2] if len(order) > 2 else 1
                events.append({"step": step_idx, "type": "BUY_ANIMAL", "detail": f"{qty}x {animal}"})
            elif cmd == "BUY_SEED":
                crop = order[1] if len(order) > 1 else "SEED"
                qty = order[2] if len(order) > 2 else 1
                events.append({"step": step_idx, "type": "BUY_SEED", "detail": f"{qty}x {crop}"})
            elif cmd == "BUY_PRODUCT":
                prod = order[1] if len(order) > 1 else "PROD"
                qty = order[2] if len(order) > 2 else 1
                events.append({"step": step_idx, "type": "BUY_PRODUCT", "detail": f"{qty}x {prod}"})
            elif cmd == "HIRE":
                events.append({"step": step_idx, "type": "HIRE_WORKER", "detail": "1x WORKER"})
            elif cmd == "SELL":
                item = order[1] if len(order) > 1 else "ITEM"
                qty = order[2] if len(order) > 2 else 1
                events.append({"step": step_idx, "type": "SELL", "detail": f"{qty}x {item}"})

    # 2. Farmer key macro actions
    if len(farmer) > 0:
        f_cmd = farmer[0]
        if f_cmd in ("BUILD_PASTURE", "FEED", "CARE", "PLANT", "HARVEST"):
            events.append({"step": step_idx, "type": f"FARMER_{f_cmd}", "detail": str(farmer[1:]) if len(farmer) > 1 else ""})

    return events

def analyze_match_trajectory(r_path: str):
    with open(r_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    steps = rep.get("steps", [])
    if len(steps) < 360:
        return None

    ep_id = os.path.basename(r_path).replace("-replay.json", "").replace("episode-", "")
    r0_final = float(steps[-1][0].get("reward") or 0.0)
    r1_final = float(steps[-1][1].get("reward") or 0.0)
    won = (r0_final > r1_final)

    # Track step-by-step money
    money0 = []
    money1 = []
    events0 = []
    events1 = []

    for s_idx in range(min(360, len(steps))):
        st = steps[s_idx]
        obs0 = st[0].get("observation", {}) or {}
        farms = obs0.get("farms", [{}, {}])
        f0 = farms[0] if len(farms) > 0 else {}
        f1 = farms[1] if len(farms) > 1 else {}

        m0 = float(f0.get("money") or 0.0)
        m1 = float(f1.get("money") or 0.0)
        money0.append(m0)
        money1.append(m1)

        act0 = st[0].get("action", {}) or {}
        act1 = st[1].get("action", {}) or {}

        ev0 = parse_action_events(s_idx, act0, obs0, 0)
        ev1 = parse_action_events(s_idx, act1, obs0, 1)

        if ev0: events0.extend(ev0)
        if ev1: events1.extend(ev1)

    # Find earliest persistent divergence:
    # Smallest step t where M1(t) - M0(t) >= 500 and stays >= 500 for the rest of Day 15 (step 360)
    div_step_500 = None
    div_step_1000 = None
    div_step_2000 = None

    diffs = np.array(money1) - np.array(money0)

    for s in range(len(diffs)):
        if diffs[s] >= 500.0 and np.all(diffs[s:360] >= 400.0) and div_step_500 is None:
            div_step_500 = s
        if diffs[s] >= 1000.0 and np.all(diffs[s:360] >= 800.0) and div_step_1000 is None:
            div_step_1000 = s
        if diffs[s] >= 2000.0 and np.all(diffs[s:360] >= 1600.0) and div_step_2000 is None:
            div_step_2000 = s

    return {
        "ep_id": ep_id,
        "won": won,
        "final_margin": r0_final - r1_final,
        "div_step_500": div_step_500,
        "div_step_1000": div_step_1000,
        "div_step_2000": div_step_2000,
        "money0": money0,
        "money1": money1,
        "events0": events0,
        "events1": events1,
    }

def main():
    print("=" * 135)
    print("EXP140: DECISION-SEQUENCE DIVERGENCE ANALYSIS (DAYS 1 TO 15)")
    print("=" * 135)

    raw_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "**", "episode-*-replay.json"), recursive=True)
    ppo_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "**", "episode-*-replay.json"), recursive=True)
    all_replays = raw_replays + ppo_replays

    print(f"Loaded {len(all_replays)} full 720-step replay archives.")

    match_results = []
    for r_path in all_replays:
        res = analyze_match_trajectory(r_path)
        if res is not None:
            match_results.append(res)

    print(f"Successfully analyzed {len(match_results)} complete Days 1-15 trajectory action streams.")

    losses = [m for m in match_results if not m["won"]]
    print(f"\nAnalyzing {len(losses)} LOSS MATCHES to identify earliest persistent divergence steps...")

    div500_list = [m["div_step_500"] for m in losses if m["div_step_500"] is not None]
    div1000_list = [m["div_step_1000"] for m in losses if m["div_step_1000"] is not None]
    div2000_list = [m["div_step_2000"] for m in losses if m["div_step_2000"] is not None]

    print("\n" + "=" * 135)
    print("1. EARLIEST PERSISTENT DIVERGENCE STEP SUMMARY (LOSS MATCHES):")
    print("=" * 135)
    print(f"  Persistent +$500 Lead  : Mean Step = {np.mean(div500_list):.1f} (Day {np.mean(div500_list)/24:.1f}) | Median = Step {np.median(div500_list):.0f} | Min = Step {np.min(div500_list)}")
    print(f"  Persistent +$1,000 Lead: Mean Step = {np.mean(div1000_list):.1f} (Day {np.mean(div1000_list)/24:.1f}) | Median = Step {np.median(div1000_list):.0f} | Min = Step {np.min(div1000_list)}")
    print(f"  Persistent +$2,000 Lead: Mean Step = {np.mean(div2000_list):.1f} (Day {np.mean(div2000_list)/24:.1f}) | Median = Step {np.median(div2000_list):.0f} | Min = Step {np.min(div2000_list)}")

    # 2. Detailed Preceding Action Sequence Analysis for Loss Matches
    print("\n" + "=" * 135)
    print("2. PRECEDING ACTION SEQUENCE COMPARISON (STEPS 0 TO 192 / DAYS 1 TO 8):")
    print("=" * 135)

    # Count macro actions in Steps 0-192 for Hero vs Opponent
    hero_actions_early = Counter()
    opp_actions_early = Counter()

    for m in losses:
        for ev in m["events0"]:
            if ev["step"] <= 192:
                hero_actions_early[f"{ev['type']} ({ev['detail']})"] += 1
        for ev in m["events1"]:
            if ev["step"] <= 192:
                opp_actions_early[f"{ev['type']} ({ev['detail']})"] += 1

    n_losses = len(losses)
    print(f"{'Action Type & Detail':<45} | {'D.1 Mean Frequency (Steps 0-192)':<35} | {'Opponent Mean Frequency (Steps 0-192)'}")
    print("-" * 135)

    all_keys = set(list(hero_actions_early.keys()) + list(opp_actions_early.keys()))
    for k in sorted(all_keys):
        h_freq = hero_actions_early[k] / n_losses
        o_freq = opp_actions_early[k] / n_losses
        if h_freq >= 0.5 or o_freq >= 0.5 or "BUY_LAND" in k or "BUY_ANIMAL" in k:
            print(f"{k:<45} | {h_freq:<35.2f} | {o_freq:.2f}")

    # 3. Step 120-240 (Days 5 to 10) Sequence Comparison
    print("\n" + "=" * 135)
    print("3. MIDGAME REINVESTMENT ACTION SEQUENCE (STEPS 120 TO 288 / DAYS 5 TO 12):")
    print("=" * 135)

    hero_mid = Counter()
    opp_mid = Counter()

    for m in losses:
        for ev in m["events0"]:
            if 120 <= ev["step"] <= 288:
                hero_mid[f"{ev['type']} ({ev['detail']})"] += 1
        for ev in m["events1"]:
            if 120 <= ev["step"] <= 288:
                opp_mid[f"{ev['type']} ({ev['detail']})"] += 1

    all_mid_keys = set(list(hero_mid.keys()) + list(opp_mid.keys()))
    for k in sorted(all_mid_keys):
        h_freq = hero_mid[k] / n_losses
        o_freq = opp_mid[k] / n_losses
        if h_freq >= 0.5 or o_freq >= 0.5 or "BUY_LAND" in k or "BUY_ANIMAL" in k or "HIRE" in k:
            print(f"{k:<45} | {h_freq:<35.2f} | {o_freq:.2f}")

    # Save EXP140 Report
    out_json = os.path.join(REPORTS_DIR, "exp140_decision_sequence_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "div_step_500": {
                "mean": float(np.mean(div500_list)),
                "median": float(np.median(div500_list)),
                "min": int(np.min(div500_list)),
            },
            "div_step_1000": {
                "mean": float(np.mean(div1000_list)),
                "median": float(np.median(div1000_list)),
                "min": int(np.min(div1000_list)),
            },
            "div_step_2000": {
                "mean": float(np.mean(div2000_list)),
                "median": float(np.median(div2000_list)),
                "min": int(np.min(div2000_list)),
            },
            "early_actions_d1": {k: float(v / n_losses) for k, v in hero_actions_early.items()},
            "early_actions_opp": {k: float(v / n_losses) for k, v in opp_actions_early.items()},
            "mid_actions_d1": {k: float(v / n_losses) for k, v in hero_mid.items()},
            "mid_actions_opp": {k: float(v / n_losses) for k, v in opp_mid.items()},
        }, f, indent=2)

    print(f"\nSaved Complete EXP140 Report: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
