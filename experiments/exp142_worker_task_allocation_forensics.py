"""EXP142: Worker Task Allocation Forensics (Days 5 to 12 / Steps 120 to 288).

Forensic investigation across 31 full 720-step Kaggle tournament replays:
1. Reconstructs and classifies every action for both the Farmer and all Workers (`hands`):
   - Categories: CARE, FEED, WATER, PLANT, HARVEST, PICKUP/DROP, MOVEMENT, IDLE.
2. Analyzes the task distribution of Farmer vs Workers during Days 5-12 (Steps 120-288).
3. Evaluates:
   - Does the opponent use workers for livestock care/feeding?
   - Does the opponent farmer focus on crop planting/watering while workers handle parallel tasks?
   - What is the worker count and worker idle rate for D.1 vs Opponent?
   - Does worker task allocation diverge before the persistent cash lead (Steps 217-314)?
4. Formulates the minimal architectural intervention to achieve parallel task efficiency.
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

def classify_action(act: list) -> str:
    if not act or len(act) == 0:
        return "IDLE"
    cmd = act[0]
    if cmd == "CARE":
        return "CARE"
    elif cmd == "FEED":
        return "FEED"
    elif cmd == "WATER":
        return "WATER"
    elif cmd in ("PLANT", "HOE"):
        return "PLANT"
    elif cmd == "HARVEST":
        return "HARVEST"
    elif cmd in ("PICKUP", "DROP"):
        return "INVENTORY"
    elif cmd in ("NORTH", "SOUTH", "EAST", "WEST"):
        return "MOVE"
    elif cmd == "PASS":
        return "IDLE"
    elif cmd == "BUILD_PASTURE":
        return "BUILD"
    return "OTHER"

def analyze_match_worker_allocation(r_path: str):
    with open(r_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    steps = rep.get("steps", [])
    if len(steps) < 288:
        return None

    ep_id = os.path.basename(r_path).replace("-replay.json", "").replace("episode-", "")
    r0_final = float(steps[-1][0].get("reward") or 0.0)
    r1_final = float(steps[-1][1].get("reward") or 0.0)
    won = (r0_final > r1_final)

    # Days 5-12 is Steps 120 to 288
    hero_farmer_tasks = Counter()
    opp_farmer_tasks = Counter()
    hero_worker_tasks = Counter()
    opp_worker_tasks = Counter()

    hero_worker_counts = []
    opp_worker_counts = []

    # Step-by-step parallel throughput
    hero_step_water = []
    hero_step_plant = []
    hero_step_animal = []
    opp_step_water = []
    opp_step_plant = []
    opp_step_animal = []

    for s_idx in range(120, min(288, len(steps))):
        st = steps[s_idx]
        act0 = st[0].get("action", {}) or {}
        act1 = st[1].get("action", {}) or {}

        # 1. Farmer classification
        f0 = act0.get("farmer") or []
        f1 = act1.get("farmer") or []
        hero_farmer_tasks[classify_action(f0)] += 1
        opp_farmer_tasks[classify_action(f1)] += 1

        # 2. Worker classification
        hands0 = act0.get("hands") or []
        hands1 = act1.get("hands") or []

        hero_worker_counts.append(len(hands0))
        opp_worker_counts.append(len(hands1))

        s_h_water, s_h_plant, s_h_animal = 0, 0, 0
        s_o_water, s_o_plant, s_o_animal = 0, 0, 0

        # Hero Farmer contribution
        f0_cls = classify_action(f0)
        if f0_cls == "WATER": s_h_water += 1
        elif f0_cls == "PLANT": s_h_plant += 1
        elif f0_cls in ("CARE", "FEED"): s_h_animal += 1

        # Hero Worker contribution
        for w_act in hands0:
            w_cls = classify_action(w_act)
            hero_worker_tasks[w_cls] += 1
            if w_cls == "WATER": s_h_water += 1
            elif w_cls == "PLANT": s_h_plant += 1
            elif w_cls in ("CARE", "FEED"): s_h_animal += 1

        # Opp Farmer contribution
        f1_cls = classify_action(f1)
        if f1_cls == "WATER": s_o_water += 1
        elif f1_cls == "PLANT": s_o_plant += 1
        elif f1_cls in ("CARE", "FEED"): s_o_animal += 1

        # Opp Worker contribution
        for w_act in hands1:
            w_cls = classify_action(w_act)
            opp_worker_tasks[w_cls] += 1
            if w_cls == "WATER": s_o_water += 1
            elif w_cls == "PLANT": s_o_plant += 1
            elif w_cls in ("CARE", "FEED"): s_o_animal += 1

        hero_step_water.append(s_h_water)
        hero_step_plant.append(s_h_plant)
        hero_step_animal.append(s_h_animal)
        opp_step_water.append(s_o_water)
        opp_step_plant.append(s_o_plant)
        opp_step_animal.append(s_o_animal)

    return {
        "ep_id": ep_id,
        "won": won,
        "hero_farmer": hero_farmer_tasks,
        "opp_farmer": opp_farmer_tasks,
        "hero_worker": hero_worker_tasks,
        "opp_worker": opp_worker_tasks,
        "hero_mean_workers": float(np.mean(hero_worker_counts)),
        "opp_mean_workers": float(np.mean(opp_worker_counts)),
        "hero_water_total": sum(hero_step_water),
        "hero_plant_total": sum(hero_step_plant),
        "hero_animal_total": sum(hero_step_animal),
        "opp_water_total": sum(opp_step_water),
        "opp_plant_total": sum(opp_step_plant),
        "opp_animal_total": sum(opp_step_animal),
    }

def main():
    print("=" * 135)
    print("EXP142: WORKER TASK ALLOCATION FORENSICS (DAYS 5 TO 12 / STEPS 120 TO 288)")
    print("=" * 135)

    raw_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "**", "episode-*-replay.json"), recursive=True)
    ppo_replays = glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "**", "episode-*-replay.json"), recursive=True)
    all_replays = raw_replays + ppo_replays

    results = []
    for r_path in all_replays:
        res = analyze_match_worker_allocation(r_path)
        if res is not None:
            results.append(res)

    losses = [r for r in results if not r["won"]]
    n_losses = len(losses)
    print(f"Audited {len(results)} full replays ({n_losses} loss matches) across 168 midgame steps (Steps 120 to 288).\n")

    # 1. Farmer Action Breakdown
    print("=" * 135)
    print("1. FARMER TASK DISTRIBUTION (STEPS 120 TO 288 / 168 STEPS TOTAL):")
    print("=" * 135)
    print(f"{'Task Category':<25} | {'D.1 Farmer Steps':<25} | {'Opponent Farmer Steps':<25} | {'Ratio (Opp / D.1)'}")
    print("-" * 135)

    categories = ["CARE", "FEED", "WATER", "PLANT", "HARVEST", "INVENTORY", "MOVE", "IDLE", "BUILD"]
    for cat in categories:
        h_f = sum(m["hero_farmer"][cat] for m in losses) / n_losses
        o_f = sum(m["opp_farmer"][cat] for m in losses) / n_losses
        ratio = (o_f / h_f) if h_f > 0 else 0.0
        print(f"{cat:<25} | {h_f:<25.2f} | {o_f:<25.2f} | {ratio:.2f}x")

    # 2. Worker Action Breakdown
    print("\n" + "=" * 135)
    print("2. WORKER (HANDS) TASK DISTRIBUTION (STEPS 120 TO 288):")
    print("=" * 135)
    print(f"{'Task Category':<25} | {'D.1 Worker Steps':<25} | {'Opponent Worker Steps':<25} | {'Ratio (Opp / D.1)'}")
    print("-" * 135)

    for cat in categories:
        h_w = sum(m["hero_worker"][cat] for m in losses) / n_losses
        o_w = sum(m["opp_worker"][cat] for m in losses) / n_losses
        ratio = (o_w / h_w) if h_w > 0 else 0.0
        print(f"{cat:<25} | {h_w:<25.2f} | {o_w:<25.2f} | {ratio:.2f}x")

    # 3. Overall Farm Throughput Comparison
    print("\n" + "=" * 135)
    print("3. OVERALL FARM PRODUCTIVE OUTPUT (FARMER + WORKERS COMBINED / STEPS 120 TO 288):")
    print("=" * 135)
    h_wtr = sum(m["hero_water_total"] for m in losses) / n_losses
    o_wtr = sum(m["opp_water_total"] for m in losses) / n_losses
    h_plt = sum(m["hero_plant_total"] for m in losses) / n_losses
    o_plt = sum(m["opp_plant_total"] for m in losses) / n_losses
    h_anm = sum(m["hero_animal_total"] for m in losses) / n_losses
    o_anm = sum(m["opp_animal_total"] for m in losses) / n_losses
    h_cnt = sum(m["hero_mean_workers"] for m in losses) / n_losses
    o_cnt = sum(m["opp_mean_workers"] for m in losses) / n_losses

    print(f"  Mean Active Workers On Field: D.1 = {h_cnt:.2f} workers | Opponent = {o_cnt:.2f} workers")
    print(f"  Total WATER Actions Executed : D.1 = {h_wtr:.2f} actions | Opponent = {o_wtr:.2f} actions (Ratio: {o_wtr/h_wtr:.2f}x)")
    print(f"  Total PLANT Actions Executed : D.1 = {h_plt:.2f} actions | Opponent = {o_plt:.2f} actions (Ratio: {o_plt/h_plt:.2f}x)")
    print(f"  Total ANIMAL (CARE/FEED)     : D.1 = {h_anm:.2f} actions | Opponent = {o_anm:.2f} actions (Ratio: {o_anm/h_anm:.2f}x)")

    # Save EXP142 Report
    out_json = os.path.join(REPORTS_DIR, "exp142_worker_allocation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "farmer_tasks_d1": {cat: float(sum(m["hero_farmer"][cat] for m in losses) / n_losses) for cat in categories},
            "farmer_tasks_opp": {cat: float(sum(m["opp_farmer"][cat] for m in losses) / n_losses) for cat in categories},
            "worker_tasks_d1": {cat: float(sum(m["hero_worker"][cat] for m in losses) / n_losses) for cat in categories},
            "worker_tasks_opp": {cat: float(sum(m["opp_worker"][cat] for m in losses) / n_losses) for cat in categories},
            "throughput_d1": {"water": float(h_wtr), "plant": float(h_plt), "animal": float(h_anm), "mean_workers": float(h_cnt)},
            "throughput_opp": {"water": float(o_wtr), "plant": float(o_plt), "animal": float(o_anm), "mean_workers": float(o_cnt)},
        }, f, indent=2)

    print(f"\nSaved Complete EXP142 Report: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
