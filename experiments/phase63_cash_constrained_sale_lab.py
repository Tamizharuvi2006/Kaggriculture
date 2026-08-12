"""
Phase 63: Cash-Constrained Sale Timing & Dynamic Liquidity Buffer Counterfactual Lab

Tests whether a Dual-Regime Liquidity Policy (unconditional immediate liquidation when below SAFE_CASH_BUFFER,
and selective market holding only when operating and reinvestment reserves are fully secured)
causally increases realized price and final wealth without starving physical compounding across 50 fresh unseen seeds (600000 + i * 137).

Experimental Matrix (3 Arms):
- Arm A (Control): Current APEX 3.4 baseline.
- Arm B (Cash-Constrained Dynamic Buffer): Unconditional sale if cash < SAFE_CASH_BUFFER(step); selective peak sale (P >= 135/110) if surplus.
- Arm C (Cash-Constrained Gentle Rebound): Unconditional sale if cash < SAFE_CASH_BUFFER(step); hold only during steep drop, exit on first positive tick or P >= 120.
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

def create_liquidity_agent(arm_name: str, base_path: str):
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

        if arm_name in ("arm_b_dynamic_buffer", "arm_c_gentle_rebound"):
            # Compute dynamic SAFE_CASH_BUFFER
            if len(unlocked) == 1:
                safe_buffer = 1100.0  # Land #2 ($1000) + seed buffer ($100)
            elif len(unlocked) == 2:
                safe_buffer = 2200.0  # Land #3 ($2000) + seed/wage buffer ($200)
            else:
                safe_buffer = 400.0   # Ongoing seed/wage/feed buffer

            is_cash_constrained = (money < safe_buffer)

            v_straw = (price_history["STRAWBERRY"][-1] - price_history["STRAWBERRY"][-2]) if len(price_history["STRAWBERRY"]) >= 2 else 0.0
            v_milk = (price_history["MILK"][-1] - price_history["MILK"][-2]) if len(price_history["MILK"]) >= 2 else 0.0

            if is_cash_constrained:
                # REGIME 1: Cash-Constrained. Unconditional liquidity execution!
                # If we have shed inventory and no sell order, inject immediate sell order
                if straw_in_shed >= 2 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                if milk_in_shed >= 2 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                    market_orders.append(["SELL", "MILK", milk_in_shed])
            else:
                # REGIME 2: Cash-Flushed. Discretionary market timing allowed!
                filtered_orders = []
                for m in market_orders:
                    if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                        item = m[1]
                        qty = int(m[2])
                        if arm_name == "arm_b_dynamic_buffer":
                            if item == "STRAWBERRY" and p_straw < 135.0 and v_straw <= 0:
                                continue  # Suppress crash sale when cash surplus exists
                            elif item == "MILK" and p_milk < 110.0 and v_milk <= 0:
                                continue
                        elif arm_name == "arm_c_gentle_rebound":
                            if item == "STRAWBERRY" and p_straw < 115.0 and v_straw < 0:
                                continue  # Suppress only steep sub-115 drops
                            elif item == "MILK" and p_milk < 95.0 and v_milk < 0:
                                continue
                    filtered_orders.append(m)

                # If peak price reached, harvest full surplus
                if p_straw >= 140.0 and straw_in_shed >= 4:
                    if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in filtered_orders):
                        filtered_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                if p_milk >= 115.0 and milk_in_shed >= 4:
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
    agent_challenger = create_liquidity_agent(arm_name, base_path)
    agent_control = create_liquidity_agent("arm_a_control", base_path)

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

    for s in range(720):
        mkt = obs.get("market") or {}
        prices = mkt.get("prices") or {}
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
        p_milk = float(prices.get("MILK", 193.0) or 193.0)

        act = agent_challenger(obs)
        if isinstance(act, dict):
            for m in (act.get("market") or []):
                if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                    item = m[1]
                    qty = int(m[2])
                    if item == "STRAWBERRY":
                        straw_rev += qty * p_straw
                        straw_vol += qty
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
    }

def run_phase63():
    print("=" * 100)
    print("🔬 PHASE 63: CASH-CONSTRAINED SALE TIMING & DYNAMIC LIQUIDITY BUFFER LAB")
    print("=" * 100)

    base_path = os.path.join(PROJECT_ROOT, "baseline", "kaitofukami-v18.py")
    test_seeds = [600000 + i * 137 for i in range(50)]

    arms = [
        "arm_a_control",
        "arm_b_dynamic_buffer",
        "arm_c_gentle_rebound",
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
    print("📊 DYNAMIC LIQUIDITY BUFFER SCORECARD (50 FRESH SEEDS)")
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
        avg_svol = np.mean([r["straw_vol"] for r in res_list])
        avg_mvol = np.mean([r["milk_vol"] for r in res_list])

        scorecard[arm] = {
            "wins": wins,
            "tot": tot,
            "win_rate": wins / tot * 100.0,
            "avg_w0": avg_w0,
            "avg_w1": avg_w1,
            "avg_d": avg_d,
            "avg_sp": avg_sp,
            "avg_mp": avg_mp,
            "avg_svol": avg_svol,
            "avg_mvol": avg_mvol,
        }
        print(f"  {arm:25s}: {wins:2d}/{tot:2d} Wins ({wins/tot*100:5.1f}%) | Wealth: ${avg_w0:10,.2f} | Delta: ${avg_d:+10,.2f} | Straw Price: ${avg_sp:6.2f} | Milk Price: ${avg_mp:6.2f} | Straw Vol: {avg_svol:5.1f}u")

    # Generate Markdown Report
    lines = []
    lines.append("# 📜 Phase 63: Cash-Constrained Sale Timing & Dynamic Liquidity Buffer Report")
    lines.append("")
    lines.append("> **Objective**: Evaluate whether a Dual-Regime Liquidity Policy (unconditional immediate liquidation when below SAFE_CASH_BUFFER, and selective market holding only when operating and reinvestment reserves are fully secured) causally increases realized price and final wealth across 50 fresh unseen seeds.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 1. Dynamic Liquidity Buffer Scorecard (50 Fresh Seeds)")
    lines.append("")
    lines.append("| Policy Arm | Description | Win Rate (/50) | Mean Wealth ($) | Net Delta ($) | Realized Straw Price | Realized Milk Price | Strawberry Volume |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for arm in arms:
        sc = scorecard[arm]
        desc = "Current APEX 3.4 Control" if arm == "arm_a_control" else "Unconditional Sale < Safe Buffer; Peak Sale if Surplus" if arm == "arm_b_dynamic_buffer" else "Unconditional Sale < Safe Buffer; Gentle Rebound Exit"
        lines.append(f"| **{arm.replace('_', ' ').title()}** | {desc} | **{sc['wins']}/{sc['tot']} ({sc['win_rate']:.1f}%)** | ${sc['avg_w0']:,.2f} | **${sc['avg_d']:+,.2f}** | ${sc['avg_sp']:.2f}/u | ${sc['avg_mp']:.2f}/u | {sc['avg_svol']:.1f} units |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💡 2. Causal Attribution & Evaluation Analysis")
    lines.append("")
    sc_a = scorecard["arm_a_control"]
    sc_b = scorecard["arm_b_dynamic_buffer"]
    sc_c = scorecard["arm_c_gentle_rebound"]

    lines.append(f"1. **Effect of Dynamic Buffer Policy (Arm B vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_b['avg_d']:+,.2f}**, Win Rate: **{sc_b['win_rate']:.1f}%**, Straw Price: **${sc_b['avg_sp']:.2f} vs ${sc_a['avg_sp']:.2f}**.")
    lines.append(f"2. **Effect of Gentle Rebound Policy (Arm C vs Control)**:")
    lines.append(f"   - Net Delta: **${sc_c['avg_d']:+,.2f}**, Win Rate: **{sc_c['win_rate']:.1f}%**, Straw Price: **${sc_c['avg_sp']:.2f} vs ${sc_a['avg_sp']:.2f}**.")

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

    report_path = os.path.join(PROJECT_ROOT, "docs", "PHASE63_LIQUIDITY_BUFFER_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nReport written successfully to: {report_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_phase63()
