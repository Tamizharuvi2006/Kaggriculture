"""
Phase 56: Opening Seed Allocation x Early Land Unlock 2x2 Factorial Counterfactual Lab

Tests whether increasing opening Strawberry seed pre-allocation (Step 106/120) and/or
accelerating early Land #2/3 unlock causally resolves the Step 143.5 planting bottleneck
across 50 fresh unseen seeds (600000 + i * 137).

Factorial Matrix (2x2):
- Arm A (Control): Current APEX 3.4 (2 seeds at Step 106, standard land timing).
- Arm B (Seed-only): +2 Strawberry seeds at Step 106/120 (4 seeds total for Day 6 clearance).
- Arm C (Land-only): Accelerated Land #2 unlock at Step 144 if cash >= $1000.
- Arm D (Combined): +2 Strawberry seeds + Accelerated Land #2 unlock.
"""

from __future__ import annotations
import os
import sys
import importlib.util
import numpy as np
import kaggle_environments
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def create_factorial_agent(arm_name: str, base_path: str):
    spec = importlib.util.spec_from_file_location(f"mod_{arm_name}", base_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base_agent = getattr(mod, "agent")

    seeds_ordered_day5 = False
    land2_ordered = False

    def agent(obs):
        nonlocal seeds_ordered_day5, land2_ordered
        step = obs.get("step", 0)
        farms = obs.get("farms") or []
        farm0 = farms[0] if len(farms) > 0 else {}
        money = float(farm0.get("money", 0.0) or 0.0)
        priv = obs.get("private") or {}
        shed = priv.get("shed") or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)
        unlocked = farm0.get("unlocked_quadrants") or ["NW"]

        # Step 71 targeted liquidity rescue (guaranteed on-time Land #2)
        if step == 71 and len(unlocked) < 2 and money < 1000.0:
            act = base_agent(obs)
            rescue_orders = []
            if milk_in_shed > 0:
                rescue_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0:
                rescue_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            if rescue_orders:
                act["market"] = rescue_orders
            return act

        act = base_agent(obs)
        if not isinstance(act, dict):
            return act

        market_orders = list(act.get("market") or [])

        # Seed Factor (Arm B & Arm D): Pre-buy +2 Strawberry seeds at Step 106 or Step 120
        if arm_name in ("arm_b_seed_only", "arm_d_combined"):
            if step in (106, 120) and not seeds_ordered_day5 and money >= 200.0:
                market_orders.append(["BUY", "STRAWBERRY_SEED", 2])
                seeds_ordered_day5 = True

        # Land Factor (Arm C & Arm D): Accelerated Land #2 unlock at Step 144 if cash >= $1000
        if arm_name in ("arm_c_land_only", "arm_d_combined"):
            if step >= 144 and len(unlocked) < 2 and money >= 1000.0 and not land2_ordered:
                market_orders.append(["BUY_LAND"])
                land2_ordered = True

        # Enforce 3-quadrant ceiling
        filtered_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            filtered_orders.append(m)
        act["market"] = filtered_orders

        return act

    return agent

def _run_match(seed: int, arm_name: str, base_path: str):
    agent_challenger = create_factorial_agent(arm_name, base_path)
    agent_control = create_factorial_agent("arm_a_control", base_path)

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    trainer = env.train([None, agent_control])
    obs = trainer.reset()

    first_plant_step = 999
    active_straw_168 = 0
    active_straw_216 = 0
    active_straw_240 = 0

    for s in range(720):
        act = agent_challenger(obs)
        obs, rew, done, info = trainer.step(act)

        if s in (168, 216, 240):
            farm0 = obs.get("farms", [{}])[0] if obs.get("farms") else {}
            straw_cnt = 0
            for row in (farm0.get("tiles") or []):
                for cell in row:
                    if isinstance(cell, dict) and cell.get("kind") == "PLANT" and cell.get("crop") == "STRAWBERRY":
                        straw_cnt += 1
            if s == 168: active_straw_168 = straw_cnt
            elif s == 216: active_straw_216 = straw_cnt
            elif s == 240: active_straw_240 = straw_cnt

        if first_plant_step == 999 and isinstance(act, dict):
            units = [act.get("farmer")] + (act.get("hands") or [])
            for u in units:
                if isinstance(u, (list, tuple)) and len(u) > 1 and u[0] == "PLANT" and u[1] == "STRAWBERRY":
                    first_plant_step = s
                    break

        if done:
            break

    state = env.state
    farms = state[0].get("observation", {}).get("farms", [])
    w0 = float(farms[0].get("money", 0.0)) if len(farms) > 0 else 0.0
    w1 = float(farms[1].get("money", 0.0)) if len(farms) > 1 else 0.0

    return {
        "seed": seed,
        "arm_name": arm_name,
        "w0": w0,
        "w1": w1,
        "delta": w0 - w1,
        "win": (w0 > w1),
        "first_plant": first_plant_step,
        "straw_168": active_straw_168,
        "straw_216": active_straw_216,
        "straw_240": active_straw_240,
    }

def run_phase56():
    print("=" * 100)
    print("🔬 PHASE 56: OPENING SEED x EARLY LAND UNLOCK 2x2 FACTORIAL COUNTERFACTUAL LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "arm_a_control",
        "arm_b_seed_only",
        "arm_c_land_only",
        "arm_d_combined",
    ]

    num_workers = min(16, os.cpu_count() or 4)
    print(f"Evaluating {len(arms)} arms across {len(test_seeds)} seeds ({len(arms)*len(test_seeds)} matches total) on {num_workers} parallel workers...\n", flush=True)

    results = {a: [] for a in arms}

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(_run_match, seed, arm, base_path)
            for arm in arms
            for seed in test_seeds
        ]
        for f in as_completed(futures):
            res = f.result()
            results[res["arm_name"]].append(res)
            icon = "🏆" if res["win"] else "❌"
            print(f"  [{res['arm_name']:20s}] Seed {res['seed']:8d} | Challenger: ${res['w0']:8.1f} vs Control: ${res['w1']:8.1f} | Delta: ${res['delta']:+8.1f} | {icon}", flush=True)

    print("\n" + "=" * 100)
    print("📊 2x2 FACTORIAL SCORECARD (50 FRESH SEEDS)")
    print("=" * 100)

    scorecard = {}
    for arm in arms:
        res_list = results[arm]
        wins = sum(1 for r in res_list if r["win"])
        tot = len(res_list)
        avg_w0 = np.mean([r["w0"] for r in res_list])
        avg_w1 = np.mean([r["w1"] for r in res_list])
        avg_d = avg_w0 - avg_w1
        avg_p1 = np.mean([r["first_plant"] for r in res_list if r["first_plant"] != 999])
        avg_s168 = np.mean([r["straw_168"] for r in res_list])
        avg_s216 = np.mean([r["straw_216"] for r in res_list])
        avg_s240 = np.mean([r["straw_240"] for r in res_list])

        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
            "avg_p1": avg_p1,
            "avg_s168": avg_s168,
            "avg_s216": avg_s216,
            "avg_s240": avg_s240,
        }
        print(f"  {arm:22s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Wealth: ${avg_w0:10,.2f} | Delta: ${avg_d:+10,.2f} | T_p1: {avg_p1:5.1f} | S@216: {avg_s216:4.1f} | S@240: {avg_s240:4.1f}")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 56: Opening Seed x Early Land Unlock 2x2 Factorial Report")
    lines.append("")
    lines.append("> **Objective**: Test whether opening Strawberry seed pre-allocation (Step 106/120) and/or accelerated Land #2 unlock (Step 144) causally resolves the Day 6 planting bottleneck across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. 2x2 Factorial Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Factorial Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | First Plant Step (T_p1) | Straw @ Step 216 | Straw @ Step 240 |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Current APEX 3.4 Control" if arm == "arm_a_control" else "+2 Strawberry Seeds at Step 106" if arm == "arm_b_seed_only" else "Accelerated Land #2 at Step 144" if arm == "arm_c_land_only" else "+2 Seeds + Accelerated Land #2"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | **${sc['avg_d']:+,.2f}** | Step {sc['avg_p1']:.1f} | {sc['avg_s216']:.1f} tiles | {sc['avg_s240']:.1f} tiles |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Causal Attribution & Interaction Analysis")
    lines.append("")
    sc_a = scorecard["arm_a_control"]
    sc_b = scorecard["arm_b_seed_only"]
    sc_c = scorecard["arm_c_land_only"]
    sc_d = scorecard["arm_d_combined"]

    lines.append(f"1. **Main Effect of Opening Seed Allocation (Arm B vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_b['avg_d']:+,.2f}**, Win Rate: **{sc_b['win_rate']:.1f}%**, Active Straw @ 240: **{sc_b['avg_s240']:.1f} vs {sc_a['avg_s240']:.1f} tiles**.")
    lines.append(f"2. **Main Effect of Early Land Unlock (Arm C vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_c['avg_d']:+,.2f}**, Win Rate: **{sc_c['win_rate']:.1f}%**, Active Straw @ 240: **{sc_c['avg_s240']:.1f} vs {sc_a['avg_s240']:.1f} tiles**.")
    lines.append(f"3. **Combined Interaction Effect (Arm D vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_d['avg_d']:+,.2f}**, Win Rate: **{sc_d['win_rate']:.1f}%**, Active Straw @ 240: **{sc_d['avg_s240']:.1f} vs {sc_a['avg_s240']:.1f} tiles**.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🛡️ 3. Project Governance Status")
    lines.append("")
    lines.append("- 🛡️ **Ref 55421857 (APEX 3.3 Challenger)**: Active live Kaggle experiment. **FROZEN & UNTOUCHED**.")
    lines.append("- 🛡️ **Ref 55249106 (V4.1 Master Baseline)**: Master Champion historical benchmark. **RETIRED**.")
    lines.append("- 🔒 **APEX 3.4**: Local research candidate. **FROZEN**.")
    lines.append("- ❌ **Kaggle Upload Status**: **NOT UPLOADED**.")
    lines.append("- 🔒 **Git Status**: **LOCAL ONLY (No push)**.")

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE56_OPENING_FACTORIAL_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase56()
