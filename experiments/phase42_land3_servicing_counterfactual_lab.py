"""
Phase 42: Land #3 / SW Quadrant Servicing & Opportunistic Task Execution Counterfactual Lab

Evaluates whether converting PASS turns into productive local task execution (HARVEST, WATER, FEED)
and active SW quadrant servicing improves wealth and win rate across 50 fresh unseen seeds (600000 + i * 137).

Experimental Arms:
1. Control: Baseline execution (untouched).
2. Arm A (Local Opportunistic Work): If worker action is PASS, execute adjacent HARVEST, WATER, or FEED.
3. Arm B (Dynamic SW Servicing): If worker is PASS and Land #3 (SW) has ready tasks, step towards SW.
4. Arm C (Full Active Servicing): Combine Local Opportunistic Work + Dynamic SW Pathing.
"""

from __future__ import annotations
import os
import sys
import importlib.util
import numpy as np
import kaggle_environments
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def get_adjacent_coords(x: int, y: int) -> List[Tuple[int, int]]:
    return [(x, y), (x+1, y), (x-1, y), (x, y+1), (x, y-1)]

def find_adjacent_task(pos: List[int], tiles: List[List[Any]]) -> str | None:
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return None
    px, py = int(pos[0]), int(pos[1])
    
    # Priority: HARVEST > FEED > WATER
    for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = px + dx, py + dy
        if 0 <= nx < 10 and 0 <= ny < 10:
            if nx < len(tiles) and ny < len(tiles[nx]):
                cell = tiles[nx][ny]
                if isinstance(cell, dict):
                    kind = cell.get("kind")
                    if kind == "PLANT" and cell.get("yield_units", 0) > 0:
                        return "HARVEST"
                    if kind == "PASTURE" and not cell.get("fed_today", True):
                        return "FEED"
                    if kind == "PASTURE" and cell.get("yield_units", 0) > 0:
                        return "COLLECT"

    # Secondary check: WATER
    for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = px + dx, py + dy
        if 0 <= nx < 10 and 0 <= ny < 10:
            if nx < len(tiles) and ny < len(tiles[nx]):
                cell = tiles[nx][ny]
                if isinstance(cell, dict) and cell.get("kind") == "PLANT":
                    if not cell.get("watered_today", True):
                        return "WATER"
    return None

def find_sw_move_direction(pos: List[int]) -> str | None:
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return None
    px, py = int(pos[0]), int(pos[1])
    # Target SW quadrant: x in [0, 4], y in [5, 9] (center at x=2, y=7)
    if py < 5:
        return "MOVE_DOWN"
    if px > 4:
        return "MOVE_LEFT"
    return None

def create_counterfactual_agent(arm_name: str, base_path: str):
    spec = importlib.util.spec_from_file_location(f"mod_{arm_name}", base_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
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
        tiles = farm0.get("tiles") or []
        farmer_pos = farm0.get("farmer")

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

        # Enforce 3-quadrant ceiling
        filtered_orders = []
        for m in (act.get("market") or []):
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            filtered_orders.append(m)
        act["market"] = filtered_orders

        if arm_name == "control":
            return act

        # Check farmer action
        farmer_act = act.get("farmer")
        is_pass = (farmer_act == ["PASS"] or farmer_act == "PASS" or not farmer_act)

        # Arm A: Local Opportunistic Work
        if arm_name == "arm_a_local_opportunistic" and is_pass:
            task = find_adjacent_task(farmer_pos, tiles)
            if task:
                act["farmer"] = [task]

        # Arm B: Dynamic SW Servicing
        elif arm_name == "arm_b_dynamic_sw" and is_pass and "SW" in unlocked:
            move_dir = find_sw_move_direction(farmer_pos)
            if move_dir:
                act["farmer"] = [move_dir]

        # Arm C: Full Active Servicing (Local Task First -> SW Move)
        elif arm_name == "arm_c_full_active_servicing" and is_pass:
            task = find_adjacent_task(farmer_pos, tiles)
            if task:
                act["farmer"] = [task]
            elif "SW" in unlocked:
                move_dir = find_sw_move_direction(farmer_pos)
                if move_dir:
                    act["farmer"] = [move_dir]

        return act

    return agent

def _run_match(seed: int, arm_name: str, base_path: str):
    agent_challenger = create_counterfactual_agent(arm_name, base_path)
    agent_benchmark = create_counterfactual_agent("control", base_path)

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    trainer = env.train([None, agent_benchmark])
    obs = trainer.reset()

    for s in range(720):
        act = agent_challenger(obs)
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
    }

def run_phase42():
    print("=" * 100)
    print("🔬 PHASE 42: LAND #3 / SW QUADRANT SERVICING & TASK EXECUTION LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "control",
        "arm_a_local_opportunistic",
        "arm_b_dynamic_sw",
        "arm_c_full_active_servicing",
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
            print(f"  [{res['arm_name']:28s}] Seed {res['seed']:8d} | Challenger: ${res['w0']:8.1f} vs Benchmark: ${res['w1']:8.1f} | Delta: ${res['delta']:+8.1f} | {icon}", flush=True)

    print("\n" + "=" * 100)
    print("📊 OVERALL TASK SERVICING SCORECARD (50 FRESH SEEDS)")
    print("=" * 100)

    scorecard = {}
    for arm in arms:
        res_list = results[arm]
        wins = sum(1 for r in res_list if r["win"])
        tot = len(res_list)
        avg_w0 = np.mean([r["w0"] for r in res_list])
        avg_w1 = np.mean([r["w1"] for r in res_list])
        avg_d = avg_w0 - avg_w1
        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
        }
        print(f"  {arm:30s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Mean Wealth: ${avg_w0:10,.2f} | Net Delta: ${avg_d:+10,.2f}")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 42: Land #3 / SW Quadrant Servicing Lab Report")
    lines.append("")
    lines.append("> **Objective**: Test whether converting PASS turns into local opportunistic task execution (HARVEST/WATER/FEED) and dynamic Land #3 (SW) servicing improves wealth across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. Counterfactual Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Experimental Arm | Strategy Description | Win Rate (/50) | Mean Challenger Wealth ($) | Mean Benchmark Wealth ($) | Net Wealth Delta ($) |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Baseline execution (untouched)" if arm == "control" else "Local Opportunistic Task Execution" if arm == "arm_a_local_opportunistic" else "Dynamic SW Quadrant Servicing" if arm == "arm_b_dynamic_sw" else "Full Active Servicing (Opportunistic + SW Pathing)"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | ${sc['avg_w1']:,.2f} | **${sc['avg_d']:+,.2f}** |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Key Empirical Findings")
    lines.append("")
    lines.append("1. **Opportunistic Action Conversion Impact**:")
    lines.append(f"   - Converting PASS turns into immediate HARVEST/WATER/FEED actions achieved **{scorecard['arm_a_local_opportunistic']['win_rate']:.1f}% win rate** with **${scorecard['arm_a_local_opportunistic']['avg_d']:+,.2f}** net wealth delta over the benchmark.")
    lines.append("2. **Dynamic SW Servicing Impact**:")
    lines.append(f"   - Dynamic pathing towards Land #3/SW achieved **{scorecard['arm_b_dynamic_sw']['win_rate']:.1f}% win rate** with **${scorecard['arm_b_dynamic_sw']['avg_d']:+,.2f}** delta.")
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

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE42_LAND3_SERVICING_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase42()
