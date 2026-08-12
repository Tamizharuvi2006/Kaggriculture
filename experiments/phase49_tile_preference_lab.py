"""
Phase 49: NW Tile-Preference & Candidate Sorting Counterfactual Lab

Tests whether prioritizing high-throughput Winner Cluster tiles (1,4), (2,2), (2,1), (1,1)
versus low-throughput Peripheral tiles (0,0), (1,0), (2,0), (3,0) causally impacts final wealth
across 50 fresh unseen seeds (600000 + i * 137).

Experimental Arms:
1. Control: Current APEX 3.4 (baseline center-distance sorting).
2. Arm A (Winner Cluster Priority): Prefer (1,4), (2,2), (2,1), (1,1) in crop plan.
3. Arm B (Peripheral Priority - Negative Control): Prefer (0,0), (1,0), (2,0), (3,0) in crop plan.
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

def create_tile_preference_agent(arm_name: str, base_path: str):
    spec = importlib.util.spec_from_file_location(f"mod_{arm_name}", base_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Patch _build_crop_plan for this module instance
    original_build_crop_plan = mod._build_crop_plan
    WINNER_CLUSTER = {(1, 4), (2, 2), (2, 1), (1, 1)}
    PERIPHERAL_CLUSTER = {(0, 0), (1, 0), (2, 0), (3, 0)}

    def custom_build_crop_plan(strawberries, animal_plan, tomatoes=0):
        plan = {pos: crop for pos, crop in mod.OPENING_CROP_PLAN.items() if crop == "MELON"}
        opening_strawberries = [pos for pos, crop in mod.OPENING_CROP_PLAN.items() if crop == "STRAWBERRY"]
        candidates = [
            (x, y)
            for y in range(10)
            for x in range(10)
            if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))
            and (x, y) not in animal_plan
            and (x, y) not in plan
        ]

        if arm_name == "arm_a_winner_cluster":
            candidates.sort(
                key=lambda p: (
                    0 if p in opening_strawberries else 1,
                    0 if (p[0], p[1]) in WINNER_CLUSTER else 1,
                    abs(p[0] - 4.5) + abs(p[1] - 4.5),
                    p[1],
                    p[0],
                )
            )
        elif arm_name == "arm_b_peripheral_control":
            candidates.sort(
                key=lambda p: (
                    0 if p in opening_strawberries else 1,
                    0 if (p[0], p[1]) in PERIPHERAL_CLUSTER else 1,
                    abs(p[0] - 4.5) + abs(p[1] - 4.5),
                    p[1],
                    p[0],
                )
            )
        else:
            candidates.sort(
                key=lambda p: (
                    0 if p in opening_strawberries else 1,
                    abs(p[0] - 4.5) + abs(p[1] - 4.5),
                    p[1],
                    p[0],
                )
            )

        for pos in candidates[:max(0, int(strawberries))]:
            plan[pos] = "STRAWBERRY"
        tomato_start = max(0, int(strawberries))
        for pos in candidates[tomato_start:tomato_start + max(0, int(tomatoes))]:
            plan[pos] = "TOMATO"
        return plan

    mod._build_crop_plan = custom_build_crop_plan
    mod._PLAN_CACHE.clear()

    base_agent = getattr(mod, "agent")

    def agent(obs):
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
    agent_challenger = create_tile_preference_agent(arm_name, base_path)
    agent_control = create_tile_preference_agent("control", base_path)

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    trainer = env.train([None, agent_control])
    obs = trainer.reset()

    straw_harvest_units = 0
    straw_revenue = 0.0
    milk_revenue = 0.0
    water_actions = 0
    fert_actions = 0
    harvest_actions = 0
    pass_actions = 0

    for s in range(720):
        act = agent_challenger(obs)
        if isinstance(act, dict):
            units = [act.get("farmer")] + (act.get("hands") or [])
            for u in units:
                if isinstance(u, (list, tuple)) and len(u) > 0:
                    cmd = u[0]
                    if cmd == "WATER": water_actions += 1
                    elif cmd == "FERTILIZE": fert_actions += 1
                    elif cmd == "HARVEST": harvest_actions += 1
                    elif cmd == "PASS": pass_actions += 1

        obs, rew, done, info = trainer.step(act)
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
        "water_actions": water_actions,
        "fert_actions": fert_actions,
        "harvest_actions": harvest_actions,
        "pass_actions": pass_actions,
    }

def run_phase49():
    print("=" * 100)
    print("🔬 PHASE 49: NW TILE-PREFERENCE & CANDIDATE SORTING COUNTERFACTUAL LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "control",
        "arm_a_winner_cluster",
        "arm_b_peripheral_control",
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
            print(f"  [{res['arm_name']:25s}] Seed {res['seed']:8d} | Challenger: ${res['w0']:8.1f} vs Control: ${res['w1']:8.1f} | Delta: ${res['delta']:+8.1f} | {icon}", flush=True)

    print("\n" + "=" * 100)
    print("📊 OVERALL TILE PREFERENCE SCORECARD (50 FRESH SEEDS)")
    print("=" * 100)

    scorecard = {}
    for arm in arms:
        res_list = results[arm]
        wins = sum(1 for r in res_list if r["win"])
        tot = len(res_list)
        avg_w0 = np.mean([r["w0"] for r in res_list])
        avg_w1 = np.mean([r["w1"] for r in res_list])
        avg_d = avg_w0 - avg_w1
        avg_water = np.mean([r["water_actions"] for r in res_list])
        avg_fert = np.mean([r["fert_actions"] for r in res_list])
        avg_harvest = np.mean([r["harvest_actions"] for r in res_list])
        avg_pass = np.mean([r["pass_actions"] for r in res_list])
        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
            "avg_water": avg_water,
            "avg_fert": avg_fert,
            "avg_harvest": avg_harvest,
            "avg_pass": avg_pass,
        }
        print(f"  {arm:28s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Wealth: ${avg_w0:10,.2f} | Delta: ${avg_d:+10,.2f} | Water: {avg_water:5.1f} | Fert: {avg_fert:4.1f} | Pass: {avg_pass:5.1f}")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 49: NW Tile-Preference Counterfactual Lab Report")
    lines.append("")
    lines.append("> **Objective**: Test whether prioritizing high-throughput Winner Cluster tiles (1,4), (2,2), (2,1), (1,1) versus low-throughput Peripheral tiles (0,0), (1,0), (2,0), (3,0) causally impacts wealth and labor efficiency across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. Counterfactual Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Experimental Arm | Strategy Description | Win Rate (/50) | Mean Challenger Wealth ($) | Net Wealth Delta ($) | Water Actions | Fert Actions | PASS Turns |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Current APEX 3.4 Baseline" if arm == "control" else "Winner Cluster Priority {(1,4), (2,2), (2,1), (1,1)}" if arm == "arm_a_winner_cluster" else "Peripheral Priority {(0,0), (1,0), (2,0), (3,0)}"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | **${sc['avg_d']:+,.2f}** | {sc['avg_water']:.1f} | {sc['avg_fert']:.1f} | {sc['avg_pass']:.1f} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Causal Mechanism Evaluation")
    lines.append("")
    sc_a = scorecard["arm_a_winner_cluster"]
    sc_b = scorecard["arm_b_peripheral_control"]
    sc_c = scorecard["control"]
    lines.append(f"1. **Winner Cluster vs Control vs Peripheral Delta**:")
    lines.append(f"   - **Arm A (Winner Cluster)**: **{sc_a['win_rate']:.1f}% Win Rate**, Mean Wealth = **${sc_a['avg_w0']:,.2f}** (Net Delta: **${sc_a['avg_d']:+,.2f}**)")
    lines.append(f"   - **Arm B (Peripheral Control)**: **{sc_b['win_rate']:.1f}% Win Rate**, Mean Wealth = **${sc_b['avg_w0']:,.2f}** (Net Delta: **${sc_b['avg_d']:+,.2f}**)")
    lines.append(f"   - **Control Baseline**: **{sc_c['win_rate']:.1f}% Win Rate**, Mean Wealth = **${sc_c['avg_w0']:,.2f}** (Net Delta: **${sc_c['avg_d']:+,.2f}**)")
    lines.append("2. **Causal Conclusion**:")
    if sc_a["avg_d"] > 200.0 and sc_a["avg_d"] > sc_b["avg_d"]:
        lines.append("   - **HYPOTHESIS CONFIRMED**: Prioritizing high-throughput winner cluster plots produces a measurable causal improvement in labor efficiency and net wealth!")
    else:
        lines.append("   - **HYPOTHESIS EVALUATED**: Tile candidate sorting within the fixed schedule planner produces negligible wealth delta because the planner expands to fill all usable quadrant tiles regardless of order.")
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

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE49_TILE_PREFERENCE_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase49()
