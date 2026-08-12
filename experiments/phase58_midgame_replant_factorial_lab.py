"""
Phase 58: Land #3 Unlock Velocity x NW Harvest Clearance Factorial Counterfactual Lab

Tests whether accelerated Land #3 unlocking (Step 240 vs Step 260) and/or
prioritizing NW 1st-generation crop harvest clearance causally expands the mid-game
Strawberry replanting pipeline across 50 fresh unseen seeds (600000 + i * 137).

Factorial Matrix (2x2):
- Arm A (Control): Current APEX 3.4 (Land #3 at Step 260, baseline harvest priority).
- Arm B (Land #3 Timing Only): Early Land #3 unlock at Step 240-241 if cash >= $2000.
- Arm C (NW Clearance Only): Prioritize NW crop harvest clearance in Steps 240-288.
- Arm D (Combined): Early Land #3 unlock + Prioritized NW clearance.
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

def create_midgame_factorial_agent(arm_name: str, base_path: str):
    spec = importlib.util.spec_from_file_location(f"mod_{arm_name}", base_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base_agent = getattr(mod, "agent")

    land3_unlocked_step = None

    def agent(obs):
        nonlocal land3_unlocked_step
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

        # Arm B & Arm D: Early Land #3 purchase at Step 240+ if cash >= $2000
        if arm_name in ("arm_b_land3_timing", "arm_d_combined"):
            if step >= 240 and "NE" in unlocked and "SW" not in unlocked and money >= 2000.0 and land3_unlocked_step is None:
                market_orders.append(["BUY_LAND"])
                land3_unlocked_step = step

        # Arm C & Arm D: NW harvest clearance boost (if a worker is near a harvestable NW tile in steps 240-288, harvest it)
        if arm_name in ("arm_c_nw_clearance", "arm_d_combined"):
            if 240 <= step <= 288:
                tiles = farm0.get("tiles") or []
                hands = farm0.get("hands") or []
                hand_acts = list(act.get("hands") or [])
                for h_idx, h_pos in enumerate(hands):
                    if h_pos and h_idx < len(hand_acts):
                        hx, hy = int(h_pos[0]), int(h_pos[1])
                        # Look for adjacent harvestable NW tile (r < 5, c < 5)
                        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1), (0,0)]:
                            nr, nc = hx + dr, hy + dc
                            if 0 <= nr < 5 and 0 <= nc < 5 and nr < len(tiles) and nc < len(tiles[nr]):
                                cell = tiles[nr][nc]
                                if isinstance(cell, dict) and cell.get("kind") == "PLANT" and int(cell.get("yield_units", 0)) > 0:
                                    if dr == 0 and dc == 0:
                                        hand_acts[h_idx] = ["HARVEST"]
                                    else:
                                        dir_map = {(-1,0): "NORTH", (1,0): "SOUTH", (0,-1): "WEST", (0,1): "EAST"}
                                        hand_acts[h_idx] = [dir_map[(dr, dc)]]
                                    break
                act["hands"] = hand_acts

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
    agent_challenger = create_midgame_factorial_agent(arm_name, base_path)
    agent_control = create_midgame_factorial_agent("arm_a_control", base_path)

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    trainer = env.train([None, agent_control])
    obs = trainer.reset()

    t_land3 = 999
    t_first_sw_plant = 999
    active_straw_profile = {}

    for s in range(720):
        farm0 = obs.get("farms", [{}])[0] if obs.get("farms") else {}
        unlocked = farm0.get("unlocked_quadrants") or ["NW"]
        if "SW" in unlocked and t_land3 == 999:
            t_land3 = s

        if s in (240, 264, 288, 312, 336, 360):
            straw_cnt = 0
            for row in (farm0.get("tiles") or []):
                for cell in row:
                    if isinstance(cell, dict) and cell.get("kind") == "PLANT" and cell.get("crop") == "STRAWBERRY":
                        straw_cnt += 1
            active_straw_profile[s] = straw_cnt

        act = agent_challenger(obs)

        # Check for first SW planting
        if t_first_sw_plant == 999 and isinstance(act, dict):
            farmer_pos = farm0.get("farmer")
            hands_pos = farm0.get("hands") or []
            units = [("farmer", act.get("farmer"), farmer_pos)]
            for h_idx, h_pos in enumerate(hands_pos):
                h_act = (act.get("hands") or [])[h_idx] if h_idx < len(act.get("hands") or []) else None
                units.append((f"hand_{h_idx}", h_act, h_pos))

            for uname, uact, upos in units:
                if isinstance(uact, (list, tuple)) and len(uact) > 1 and uact[0] == "PLANT" and uact[1] == "STRAWBERRY" and upos:
                    ur, uc = int(upos[0]), int(upos[1])
                    if ur >= 5 and uc < 5:  # SW Quadrant
                        t_first_sw_plant = s
                        break

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
        "t_land3": t_land3,
        "t_first_sw_plant": t_first_sw_plant,
        "land3_latency": (t_first_sw_plant - t_land3) if (t_first_sw_plant != 999 and t_land3 != 999) else 999,
        "straw_profile": active_straw_profile,
    }

def run_phase58():
    print("=" * 100)
    print("🔬 PHASE 58: LAND #3 UNLOCK VELOCITY x NW HARVEST CLEARANCE 2x2 FACTORIAL LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "arm_a_control",
        "arm_b_land3_timing",
        "arm_c_nw_clearance",
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
        avg_l3 = np.mean([r["t_land3"] for r in res_list if r["t_land3"] != 999])
        avg_sw_p = np.mean([r["t_first_sw_plant"] for r in res_list if r["t_first_sw_plant"] != 999])
        avg_lat = np.mean([r["land3_latency"] for r in res_list if r["land3_latency"] != 999])
        avg_s240 = np.mean([r["straw_profile"].get(240, 0) for r in res_list])
        avg_s288 = np.mean([r["straw_profile"].get(288, 0) for r in res_list])
        avg_s360 = np.mean([r["straw_profile"].get(360, 0) for r in res_list])

        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
            "avg_l3": avg_l3,
            "avg_sw_p": avg_sw_p,
            "avg_lat": avg_lat,
            "avg_s240": avg_s240,
            "avg_s288": avg_s288,
            "avg_s360": avg_s360,
        }
        print(f"  {arm:22s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Wealth: ${avg_w0:10,.2f} | Delta: ${avg_d:+10,.2f} | L3: {avg_l3:5.1f} | SW_P1: {avg_sw_p:5.1f} | Lat: {avg_lat:4.1f}s | S@360: {avg_s360:4.1f}")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 58: Land #3 Unlock Velocity x NW Harvest Clearance Factorial Report")
    lines.append("")
    lines.append("> **Objective**: Evaluate whether accelerated Land #3 unlocking (Step 240 vs Step 260) and/or prioritized NW harvest clearance causally expands the mid-game Strawberry pipeline across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. 2x2 Factorial Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Factorial Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Land #3 Step (T_l3) | SW Plant Step (T_sw) | Unlock->Plant Latency | Straw @ 360 |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Current APEX 3.4 Control" if arm == "arm_a_control" else "Land #3 at Step 240+ if Cash >= $2k" if arm == "arm_b_land3_timing" else "Prioritized NW Harvest Clearance" if arm == "arm_c_nw_clearance" else "Early Land #3 + NW Clearance"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | **${sc['avg_d']:+,.2f}** | Step {sc['avg_l3']:.1f} | Step {sc['avg_sw_p']:.1f} | **{sc['avg_lat']:.1f} steps** | **{sc['avg_s360']:.1f} tiles** |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Causal Attribution & Interaction Analysis")
    lines.append("")
    sc_a = scorecard["arm_a_control"]
    sc_b = scorecard["arm_b_land3_timing"]
    sc_c = scorecard["arm_c_nw_clearance"]
    sc_d = scorecard["arm_d_combined"]

    lines.append(f"1. **Main Effect of Land #3 Unlock Velocity (Arm B vs Control)**:")
    lines.append(f"   - Land #3 Step: **Step {sc_b['avg_l3']:.1f} vs Step {sc_a['avg_l3']:.1f}** ({sc_a['avg_l3'] - sc_b['avg_l3']:.1f} steps faster).")
    lines.append(f"   - Net Delta: **${sc_b['avg_d']:+,.2f}**, Win Rate: **{sc_b['win_rate']:.1f}%**, Straw @ 360: **{sc_b['avg_s360']:.1f} vs {sc_a['avg_s360']:.1f} tiles**.")
    lines.append(f"2. **Main Effect of NW Harvest Clearance (Arm C vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_c['avg_d']:+,.2f}**, Win Rate: **{sc_c['win_rate']:.1f}%**, Straw @ 360: **{sc_c['avg_s360']:.1f} vs {sc_a['avg_s360']:.1f} tiles**.")
    lines.append(f"3. **Combined Interaction Effect (Arm D vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_d['avg_d']:+,.2f}**, Win Rate: **{sc_d['win_rate']:.1f}%**, Straw @ 360: **{sc_d['avg_s360']:.1f} vs {sc_a['avg_s360']:.1f} tiles**.")

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

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE58_MIDGAME_FACTORIAL_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase58()
