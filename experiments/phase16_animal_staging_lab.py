"""PHASE 16: PARALLEL ANIMAL STAGING & CAPITAL ALLOCATION COUNTERFACTUAL TOURNAMENT.

Objective: Causally evaluate whether staging animal acquisitions (delaying Cow #2 to Day 2 and adding Cow #3)
improves capital compounding, strawberry throughput, and head-to-head win rate against V4.1 Master Opponent.

Evaluated in parallel across 50 unseen seeds under Kaggle 24-step clearance parity (townCenterSellInterval = 24).
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

# Global worker state initialized once per process
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

    cows_bought = 0
    cow2_purchased = False
    cow3_purchased = False

    def staged_agent(obs):
        nonlocal cows_bought, cow2_purchased, cow3_purchased
        step = int(obs.get("step", 0) or 0)
        if step == 0:
            cows_bought = 0
            cow2_purchased = False
            cow3_purchased = False

        act = _WORKER_V41_AGENT(obs)
        if not act or not isinstance(act, dict):
            return act

        market_orders = act.get("market") or []
        filtered_market = []

        farms = obs.get("farms") or []
        player_idx = int(obs.get("player", 0) or 0)
        farm = farms[player_idx] if len(farms) > player_idx else {}
        cash = float(farm.get("money", 0.0) or 0.0)
        hands = farm.get("hands") or []
        num_workers = len(hands) + 1

        for order in market_orders:
            if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "BUY_ANIMAL" and order[1] == "COW":
                if mode == "control":
                    filtered_market.append(order)
                    cows_bought += 1
                elif mode in ["arm_a", "arm_b", "arm_c"]:
                    if cows_bought == 0:
                        filtered_market.append(order)
                        cows_bought += 1
            else:
                filtered_market.append(order)

        if mode == "arm_a":
            if step == 24 and not cow2_purchased and cash >= 900.0 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow2_purchased = True
                cows_bought += 1
            elif step == 48 and not cow3_purchased and cash >= 900.0 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow3_purchased = True
                cows_bought += 1

        elif mode == "arm_b":
            if not cow2_purchased and cows_bought >= 1 and num_workers >= 4 and cash >= 1200.0 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow2_purchased = True
                cows_bought += 1
            elif not cow3_purchased and cow2_purchased and num_workers >= 5 and cash >= 1200.0 and step <= 200 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow3_purchased = True
                cows_bought += 1

        elif mode == "arm_c":
            if not cow2_purchased and cows_bought >= 1 and num_workers >= 4 and cash >= 1500.0 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow2_purchased = True
                cows_bought += 1
            elif not cow3_purchased and cow2_purchased and num_workers >= 5 and cash >= 1600.0 and step <= 200 and len(filtered_market) < 5:
                filtered_market.append(["BUY_ANIMAL", "COW", 1])
                cow3_purchased = True
                cows_bought += 1

        return {
            "farmer": list(act.get("farmer") or ["PASS"]),
            "hands": [list(h) for h in (act.get("hands") or [])],
            "market": filtered_market
        }

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, _WORKER_V41_AGENT])
    obs = trainer.reset()

    total_milk_rev = 0.0
    total_straw_rev = 0.0
    c50 = 0.0

    for s in range(720):
        act = staged_agent(obs)
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

        obs, rew, done, info = trainer.step(act)
        if s == 50:
            farms = obs.get("farms") or []
            c50 = float(farms[0].get("money", 0.0) or 0.0) if farms else 0.0
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
        "cash_step50": c50,
        "win": 1 if w_agent > w_opp else 0,
        "loss": 1 if w_agent < w_opp else 0,
        "tie": 1 if w_agent == w_opp else 0,
    }

def run_phase16():
    processes = 4
    print("====================================================================================================", flush=True)
    print(f"🔬 PHASE 16: PARALLEL ANIMAL STAGING LAB ({processes} DEDICATED PROCESS WORKERS | 50 SEEDS)", flush=True)
    print("====================================================================================================", flush=True)

    seeds = [60000 + i * 29 for i in range(50)]
    print(f"Total Test Seeds: {len(seeds)} | Environment: townCenterSellInterval = 24\n", flush=True)

    arms = [
        ("Control (V4.1 Master Baseline: Cow#1@0, Cow#2@1)", "control"),
        ("Arm A (Fixed Staging: Cow#2@24, Cow#3@48)", "arm_a"),
        ("Arm B (Labor & Liquidity Gated: Workers>=4, Cash>=$1.2k)", "arm_b"),
        ("Arm C (State-Conditioned Dynamic Runway: Cash>=$1.5k)", "arm_c"),
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
            avg_c50 = sum(r["cash_step50"] for r in results) / len(results)

            print(f"  Wealth: ${avg_w:,.2f} vs Opponent: ${avg_opp_w:,.2f} | Win Rate: {win_rate:.1f}% ({wins}W-{losses}L-{ties}T)")
            print(f"  Milk Rev: ${avg_milk:,.2f} | Straw Rev: ${avg_straw:,.2f} | Cash @ Step 50: ${avg_c50:,.2f}\n", flush=True)

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
                "cash_step50": avg_c50,
            })

    report_md = f"""# 📜 Phase 16: Animal Staging & Capital Allocation Counterfactual Tournament Report

> **Research Purpose**: Parallel causal counterfactual evaluation of **Animal Staging & Capital Allocation** (delaying Cow #2 and adding Cow #3) across **50 unseen seeds** under strict Kaggle 24-step clearance parity against the protected V4.1 Master Opponent.
> **Objective**: Determine whether staging early livestock purchases unlocks early crop working capital, accelerates strawberry throughput, and breaks the 1200–1400 rating ceiling.

---

## 📊 1. Master Head-to-Head Tournament Results (50 Unseen Seeds, 24-Step Clearance)

| Strategy Arm / Configuration | Mean Wealth ($) | Opponent Wealth ($) | Head-to-Head Win Rate | Milk Revenue ($) | Strawberry Revenue ($) | Cash @ Step 50 ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for r in all_results:
        report_md += f"| **{r['arm_name']}** | **${r['wealth']:,.2f}** | ${r['opp_wealth']:,.2f} | **{r['win_rate']:.1f}%** ({r['wins']}W-{r['losses']}L) | ${r['milk_revenue']:,.2f} | ${r['straw_revenue']:,.2f} | ${r['cash_step50']:,.2f} |\n"

    report_md += f"""
---

## 🔍 2. Key Empirical Findings & Causal Insights

1. **Early Working Capital Velocity**:
   - Compares opening liquidity at Step 50 between immediate Cow #2 purchase vs staged acquisition.

2. **Crop & Livestock Revenue Interplay**:
   - Measures whether delaying Cow #2 allows earlier/larger Strawberry seed deployments without hurting lifetime Milk yield.

3. **Competitive Edge vs V4.1 Master**:
   - Tests whether any staged configuration achieves Pareto superiority over standard V4.1 baseline.

---

## 🏛️ Governance, Baseline Protection & Code Integrity

- 🛡️ **V4.1 Master Champion (Ref `55249106`, 1479.8 public / 1714.4 live)**: **100% PROTECTED & UNTOUCHED**.
- 📦 **APEX 3.0 (Ref `55411304`, 1191.0)**: Preserved as historical Kaggle benchmark.
- 🔒 **APEX 3.2 Candidate**: Frozen locally (0 uploads executed).
- 🎯 **Challenger Upload Directive**: Only when a staged animal candidate demonstrates strict Pareto-dominance across all 50 seeds will a formal candidate be considered.
"""

    report_path = os.path.join(BASE_DIR, "docs", "PHASE16_ANIMAL_STAGING_LAB_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Report written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_phase16()
