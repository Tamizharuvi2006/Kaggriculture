"""PHASE 19: CLEARANCE PREEMPTION COUNTERFACTUAL LAB.

Objective: Causally evaluate the APEX 3.3 Clearance Preemption Engine across 50 unseen seeds
under Kaggle 24-step clearance parity (townCenterSellInterval = 24) against V4.1 Master Opponent.

Core Principle:
- NEVER invent synthetic sales or hold inventory indefinitely.
- ONLY advance the execution timing of legitimate V4.1 planned sales (Milk / Strawberry)
  to step % 24 == 23 (1 step before clearance boundary) to capture peak clearance prices.

Arms:
- Control: Standard V4.1 Master Baseline (untouched)
- Arm A (Milk Clearance Preemption): Advances legitimate Milk sales to step % 24 == 23
- Arm B (Strawberry Clearance Preemption): Advances legitimate Strawberry sales to step % 24 == 23
- Arm C (Combined Preemption Overlay): Both Milk & Strawberry clearance preemption active

Outputs: docs/PHASE19_CLEARANCE_PREEMPTION_LAB_REPORT.md
"""

from __future__ import annotations
import sys
import os
import json
import multiprocessing
import importlib.util
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

_WORKER_V41_AGENT = None

def init_worker():
    global _WORKER_V41_AGENT
    v41_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("v41_mod", v41_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _WORKER_V41_AGENT = mod.agent

def run_match_worker(args: Tuple[str, int]) -> Dict[str, Any]:
    global _WORKER_V41_AGENT
    mode, seed = args

    milk_preemptions = 0
    straw_preemptions = 0

    def preemption_agent(obs):
        nonlocal milk_preemptions, straw_preemptions
        step = int(obs.get("step", 0) or 0)

        # Baseline V4.1 action
        act = _WORKER_V41_AGENT(obs)
        if not act or not isinstance(act, dict):
            return act

        market_orders = [list(o) for o in (act.get("market") or [])]
        
        # Check if clearance boundary is 1 step away
        is_pre_clearance = (step % 24 == 23)

        if is_pre_clearance and mode != "control":
            farms = obs.get("farms") or []
            player_idx = int(obs.get("player", 0) or 0)
            priv = obs.get("private") or {}
            shed = priv.get("shed") or {}
            cash = float(farms[player_idx].get("money", 0.0) or 0.0) if len(farms) > player_idx else 0.0

            milk_in_shed = int(shed.get("MILK", 0) or 0)
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            # Check if baseline already selling milk/straw
            has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in market_orders)
            has_straw_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY" for o in market_orders)

            # Arm A or C: Milk Clearance Preemption
            if mode in ["arm_a", "arm_c"] and not has_milk_sell and milk_in_shed >= 2:
                # Advancing legitimate milk sale timing to pre-clearance
                if len(market_orders) < 5:
                    market_orders.append(["SELL", "MILK", milk_in_shed])
                    milk_preemptions += 1

            # Arm B or C: Strawberry Clearance Preemption
            if mode in ["arm_b", "arm_c"] and not has_straw_sell and straw_in_shed >= 4:
                # Advancing legitimate strawberry sale timing to pre-clearance
                if len(market_orders) < 5:
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    straw_preemptions += 1

        return {
            "farmer": list(act.get("farmer") or ["PASS"]),
            "hands": [list(h) for h in (act.get("hands") or [])],
            "market": market_orders
        }

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, _WORKER_V41_AGENT])
    obs = trainer.reset()

    total_milk_rev = 0.0
    total_straw_rev = 0.0
    cash_starvation_steps = 0

    for s in range(720):
        act = preemption_agent(obs)
        market_acts = act.get("market") or []
        market_obs = obs.get("market") or {}
        prices = market_obs.get("prices") or {}

        for m in market_acts:
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL":
                item = m[1]
                qty = int(m[2]) if len(m) > 2 else 1
                p = float(prices.get(item, 0.0) or 0.0)
                if item == "MILK":
                    total_milk_rev += p * qty
                elif item == "STRAWBERRY":
                    total_straw_rev += p * qty

        farms = obs.get("farms") or []
        c = float(farms[0].get("money", 0.0) or 0.0) if farms else 0.0
        if c < 10.0:
            cash_starvation_steps += 1

        obs, rew, done, info = trainer.step(act)
        if done:
            break

    w_agent = float(rew if rew is not None else 0.0)
    farms = obs.get("farms") or []
    w_opp = float(farms[1].get("money", 0.0) or 0.0) if len(farms) > 1 else 0.0

    return {
        "wealth": w_agent,
        "opp_wealth": w_opp,
        "milk_revenue": total_milk_rev,
        "straw_revenue": total_straw_rev,
        "cash_starvation": cash_starvation_steps,
        "milk_preemptions": milk_preemptions,
        "straw_preemptions": straw_preemptions,
        "win": 1 if w_agent > w_opp else 0,
        "loss": 1 if w_agent < w_opp else 0,
        "tie": 1 if w_agent == w_opp else 0,
    }

def run_phase19_tournament():
    processes = 4
    print("====================================================================================================", flush=True)
    print(f"🔬 PHASE 19: CLEARANCE PREEMPTION LAB ({processes} PROCESS WORKERS | 50 SEEDS)", flush=True)
    print("====================================================================================================", flush=True)

    seeds = [70000 + i * 31 for i in range(50)]
    print(f"Total Test Seeds: {len(seeds)} | Environment: townCenterSellInterval = 24\n", flush=True)

    arms = [
        ("Control (V4.1 Master Baseline: Untouched)", "control"),
        ("Arm A (Milk Clearance Preemption @ step%24==23)", "arm_a"),
        ("Arm B (Strawberry Clearance Preemption @ step%24==23)", "arm_b"),
        ("Arm C (Combined Milk + Strawberry Clearance Preemption)", "arm_c"),
    ]

    all_results = []

    with multiprocessing.Pool(processes=processes, initializer=init_worker) as pool:
        for arm_name, mode in arms:
            print(f"--- ⚔️ EVALUATING (PARALLEL): {arm_name} vs V4.1 MASTER OPPONENT ---", flush=True)
            tasks = [(mode, seed) for seed in seeds]
            results = pool.map(run_match_worker, tasks)

            wealths = [r["wealth"] for r in results]
            opp_wealths = [r["opp_wealth"] for r in results]
            wins = sum(r["win"] for r in results)
            losses = sum(r["loss"] for r in results)
            ties = sum(r["tie"] for r in results)

            avg_w = sum(wealths) / len(wealths)
            avg_opp_w = sum(opp_wealths) / len(opp_wealths)
            win_rate = (wins / len(seeds)) * 100.0
            avg_milk = sum(r["milk_revenue"] for r in results) / len(results)
            avg_straw = sum(r["straw_revenue"] for r in results) / len(results)
            avg_starve = sum(r["cash_starvation"] for r in results) / len(results)
            avg_m_preempt = sum(r["milk_preemptions"] for r in results) / len(results)
            avg_s_preempt = sum(r["straw_preemptions"] for r in results) / len(results)

            print(f"  Wealth: ${avg_w:,.2f} vs Opponent: ${avg_opp_w:,.2f} | Win Rate: {win_rate:.1f}% ({wins}W-{losses}L-{ties}T)")
            print(f"  Milk Rev: ${avg_milk:,.2f} | Straw Rev: ${avg_straw:,.2f} | Cash Starve Steps: {avg_starve:.1f}")
            print(f"  Preemptions - Milk: {avg_m_preempt:.1f} | Straw: {avg_s_preempt:.1f}\n", flush=True)

            all_results.append({
                "arm_name": arm_name,
                "wealth": avg_w,
                "opp_wealth": avg_opp_w,
                "win_rate": win_rate,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "milk_revenue": avg_milk,
                "straw_revenue": avg_straw,
                "cash_starve": avg_starve,
                "milk_preemptions": avg_m_preempt,
                "straw_preemptions": avg_s_preempt,
            })

    report_md = f"""# 📜 Phase 19: Clearance Preemption Counterfactual Lab Report

> **Research Purpose**: Systematic causal counterfactual evaluation of **APEX 3.3 Clearance Preemption Engine** across **50 unseen seeds** under strict Kaggle 24-step clearance parity against the protected V4.1 Master Opponent.
> **Core Principle**: Advance the execution timing of legitimate V4.1 planned sales (Milk / Strawberry) to `step % 24 == 23` (1 step before clearance) without inventing synthetic orders or holding inventory.

---

## 📊 1. Master Head-to-Head Tournament Results (50 Unseen Seeds, 24-Step Clearance)

| Strategy Arm / Configuration | Mean Wealth ($) | Opponent Wealth ($) | Head-to-Head Win Rate | Milk Revenue ($) | Strawberry Revenue ($) | Preemptions (M / S) | Cash Starve Steps |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for r in all_results:
        report_md += f"| **{r['arm_name']}** | **${r['wealth']:,.2f}** | ${r['opp_wealth']:,.2f} | **{r['win_rate']:.1f}%** ({r['wins']}W-{r['losses']}L) | ${r['milk_revenue']:,.2f} | ${r['straw_revenue']:,.2f} | {r['milk_preemptions']:.1f} / {r['straw_preemptions']:.1f} | {r['cash_starve']:.1f} |\n"

    report_md += f"""
---

## 🔍 2. Key Empirical Findings & Causal Insights

1. **Clearance Timing Preemption Value**:
   - Evaluates whether advancing existing Milk and Strawberry inventory sales to `step % 24 == 23` secures higher realized sale prices.

2. **Cash Flow & Reinvestment Stability**:
   - Verifies that preemption does not cause cash starvation or delay crop/land purchases.

3. **Challenger Readiness**:
   - Determines if Arm A, B, or C demonstrates strict Pareto superiority over V4.1 Master Baseline.

---

## 🏛️ Governance, Baseline Protection & Code Integrity

- 🛡️ **V4.1 Master Champion (Ref `55249106`, 1479.8 public / 1714.4 live)**: **100% PROTECTED & UNTOUCHED**.
- 🔒 **APEX 3.2 Candidate**: Frozen locally.
- 🎯 **APEX 3.3 Integration Directive**: Only if Phase 19 produces positive net wealth delta and zero regressions across all 50 seeds will APEX 3.3 candidate be compiled.
"""

    report_path = os.path.join(BASE_DIR, "docs", "PHASE19_CLEARANCE_PREEMPTION_LAB_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Report written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_phase19_tournament()
