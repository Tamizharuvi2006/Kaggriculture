"""
Phase 62: Price-Velocity Market Regime Counterfactual Lab

Tests whether momentum-aware market overlays (avoiding VALLEY_CRASH and/or accelerating PEAK sales)
causally increase realized price and final wealth without starving operating reserves across 50 fresh unseen seeds (600000 + i * 137).

Experimental Matrix (3 Arms):
- Arm A (Control): Current APEX 3.4 baseline.
- Arm B (Crash Avoidance): Suppress sales during VALLEY_CRASH (P < 135/110 and v <= 0) unless money < operating reserve ($100).
- Arm C (Crash Avoidance + Peak Acceleration): Suppress VALLEY_CRASH + immediately liquidate shed inventory when entering PEAK regimes (P >= 135/110).
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

def create_regime_agent(arm_name: str, base_path: str):
    spec = importlib.util.spec_from_file_location(f"mod_{arm_name}", base_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base_agent = getattr(mod, "agent")

    price_history = {"STRAWBERRY": [], "MILK": []}

    def agent(obs):
        nonlocal price_history
        step = obs.get("step", 0)
        farms = obs.get("farms") or []
        farm0 = farms[0] if len(farms) > 0 else {}
        money = float(farm0.get("money", 0.0) or 0.0)
        priv = obs.get("private") or {}
        shed = priv.get("shed") or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        unlocked = farm0.get("unlocked_quadrants") or ["NW"]

        # Track price history
        mkt = obs.get("market") or {}
        prices = mkt.get("prices") or {}
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
        p_milk = float(prices.get("MILK", 193.0) or 193.0)

        price_history["STRAWBERRY"].append(p_straw)
        price_history["MILK"].append(p_milk)

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

        # End of game clearance (steps >= 700): force sell everything
        if step >= 700:
            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            if clean_orders:
                act["market"] = clean_orders
            return act

        if arm_name in ("arm_b_crash_avoidance", "arm_c_crash_and_peak"):
            # Compute velocity
            v_straw = (price_history["STRAWBERRY"][-1] - price_history["STRAWBERRY"][-2]) if len(price_history["STRAWBERRY"]) >= 2 else 0.0
            v_milk = (price_history["MILK"][-1] - price_history["MILK"][-2]) if len(price_history["MILK"]) >= 2 else 0.0

            # Guardrail: Operating reserve ($100 for feed and wages)
            has_liquidity = (money >= 100.0)

            filtered_orders = []
            for m in market_orders:
                if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                    item = m[1]
                    qty = int(m[2])
                    if item == "STRAWBERRY":
                        is_crash = (p_straw < 135.0 and v_straw <= 0.0)
                        if is_crash and has_liquidity:
                            continue  # Suppress crash sale
                    elif item == "MILK":
                        is_crash = (p_milk < 110.0 and v_milk <= 0.0)
                        if is_crash and has_liquidity:
                            continue  # Suppress crash sale
                filtered_orders.append(m)

            # Arm C Peak Acceleration: If in PEAK regime and have inventory, execute peak sale
            if arm_name == "arm_c_crash_and_peak":
                if p_straw >= 135.0 and straw_in_shed >= 4:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in filtered_orders):
                        filtered_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                if p_milk >= 110.0 and milk_in_shed >= 4:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in filtered_orders):
                        filtered_orders.append(["SELL", "MILK", milk_in_shed])

            market_orders = filtered_orders

        # Enforce 3-quadrant ceiling
        final_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(m)
        act["market"] = final_orders

        return act

    return agent

def _run_match(seed: int, arm_name: str, base_path: str):
    agent_challenger = create_regime_agent(arm_name, base_path)
    agent_control = create_regime_agent("arm_a_control", base_path)

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    trainer = env.train([None, agent_control])
    obs = trainer.reset()

    straw_rev = 0.0
    straw_vol = 0
    milk_rev = 0.0
    milk_vol = 0
    peak_straw_vol = 0
    crash_straw_vol = 0

    price_history = {"STRAWBERRY": [], "MILK": []}

    for s in range(720):
        mkt = obs.get("market") or {}
        prices = mkt.get("prices") or {}
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
        p_milk = float(prices.get("MILK", 193.0) or 193.0)
        price_history["STRAWBERRY"].append(p_straw)
        price_history["MILK"].append(p_milk)

        v_straw = (price_history["STRAWBERRY"][-1] - price_history["STRAWBERRY"][-2]) if len(price_history["STRAWBERRY"]) >= 2 else 0.0

        act = agent_challenger(obs)
        if isinstance(act, dict):
            for m in (act.get("market") or []):
                if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                    item = m[1]
                    qty = int(m[2])
                    if item == "STRAWBERRY":
                        straw_rev += qty * p_straw
                        straw_vol += qty
                        if p_straw >= 135.0: peak_straw_vol += qty
                        elif p_straw < 135.0 and v_straw <= 0.0: crash_straw_vol += qty
                    elif item == "MILK":
                        milk_rev += qty * p_milk
                        milk_vol += qty

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
        "straw_rev": straw_rev,
        "straw_vol": straw_vol,
        "straw_price": (straw_rev / straw_vol) if straw_vol > 0 else 0.0,
        "milk_rev": milk_rev,
        "milk_vol": milk_vol,
        "milk_price": (milk_rev / milk_vol) if milk_vol > 0 else 0.0,
        "peak_straw_pct": (peak_straw_vol / straw_vol * 100.0) if straw_vol > 0 else 0.0,
        "crash_straw_pct": (crash_straw_vol / straw_vol * 100.0) if straw_vol > 0 else 0.0,
    }

def run_phase62():
    print("=" * 100)
    print("🔬 PHASE 62: PRICE-VELOCITY MARKET REGIME COUNTERFACTUAL LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "arm_a_control",
        "arm_b_crash_avoidance",
        "arm_c_crash_and_peak",
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
    print("📊 PRICE-VELOCITY REGIME SCORECARD (50 FRESH SEEDS)")
    print("=" * 100)

    scorecard = {}
    for arm in arms:
        res_list = results[arm]
        wins = sum(1 for r in res_list if r["win"])
        tot = len(res_list)
        avg_w0 = np.mean([r["w0"] for r in res_list])
        avg_w1 = np.mean([r["w1"] for r in res_list])
        avg_d = avg_w0 - avg_w1
        avg_sp = np.mean([r["straw_price"] for r in res_list])
        avg_mp = np.mean([r["milk_price"] for r in res_list])
        avg_peak = np.mean([r["peak_straw_pct"] for r in res_list])
        avg_crash = np.mean([r["crash_straw_pct"] for r in res_list])

        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
            "avg_sp": avg_sp,
            "avg_mp": avg_mp,
            "avg_peak": avg_peak,
            "avg_crash": avg_crash,
        }
        print(f"  {arm:25s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Wealth: ${avg_w0:10,.2f} | Delta: ${avg_d:+10,.2f} | Straw Price: ${avg_sp:6.2f} | Milk Price: ${avg_mp:6.2f} | Peak%: {avg_peak:4.1f}% | Crash%: {avg_crash:4.1f}%")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 62: Price-Velocity Market Regime Counterfactual Report")
    lines.append("")
    lines.append("> **Objective**: Test whether momentum-aware market overlays (suppressing VALLEY_CRASH sales and accelerating PEAK liquidations) causally increase realized prices and wealth across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. Price-Velocity Regime Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Policy Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Realized Straw Price | Realized Milk Price | Peak Sale % | Crash Sale % |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Current APEX 3.4 Control" if arm == "arm_a_control" else "Suppress VALLEY_CRASH (P<135/110, v<=0)" if arm == "arm_b_crash_avoidance" else "Suppress Crash + Accelerate Peak Sales"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | **${sc['avg_d']:+,.2f}** | ${sc['avg_sp']:.2f}/u | ${sc['avg_mp']:.2f}/u | {sc['avg_peak']:.1f}% | {sc['avg_crash']:.1f}% |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Causal Attribution & Evaluation Analysis")
    lines.append("")
    sc_a = scorecard["arm_a_control"]
    sc_b = scorecard["arm_b_crash_avoidance"]
    sc_c = scorecard["arm_c_crash_and_peak"]

    lines.append(f"1. **Effect of Crash-Dumping Avoidance (Arm B vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_b['avg_d']:+,.2f}**, Win Rate: **{sc_b['win_rate']:.1f}%**, Crash Sale Rate: **{sc_b['avg_crash']:.1f}% vs {sc_a['avg_crash']:.1f}%**.")
    lines.append(f"2. **Effect of Peak Sale Acceleration (Arm C vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_c['avg_d']:+,.2f}**, Win Rate: **{sc_c['win_rate']:.1f}%**, Peak Sale Rate: **{sc_c['avg_peak']:.1f}% vs {sc_a['avg_peak']:.1f}%**.")

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

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE62_MARKET_REGIME_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase62()
