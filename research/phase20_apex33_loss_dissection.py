"""PHASE 20: MICRO-DISSECTION OF THE 13 APEX 3.3 LOSSES.

Investigates the exact 13 loss matches out of the 50-seed Phase 19 tournament where APEX 3.3 (Arm C)
was defeated by the V4.1 Master Opponent.

Tracks for each loss seed:
- Seed number & final wealth gap (Our Wealth vs Opponent Wealth)
- First divergence step T (where opponent wealth lead > $1500)
- Commodity state at divergence (Milk inventory, Strawberry inventory)
- Market prices & clearance timing (step % 24)
- Opponent market action vs Our market action in window [T-24, T+24]
- Loss Root Cause Taxonomy & Cluster Analysis

Outputs: docs/PHASE20_APEX33_LOSS_DISSECTION_REPORT.md
"""

from __future__ import annotations
import sys
import os
import json
import importlib.util
from collections import defaultdict
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def load_v41_baseline():
    v41_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("v41_mod", v41_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

v41_master_agent = load_v41_baseline()

def create_apex33_agent():
    milk_preemptions = 0
    straw_preemptions = 0

    def agent(obs):
        nonlocal milk_preemptions, straw_preemptions
        step = int(obs.get("step", 0) or 0)
        act = v41_master_agent(obs)
        if not act or not isinstance(act, dict):
            return act

        market_orders = [list(o) for o in (act.get("market") or [])]
        is_pre_clearance = (step % 24 == 23)

        if is_pre_clearance:
            farms = obs.get("farms") or []
            player_idx = int(obs.get("player", 0) or 0)
            priv = obs.get("private") or {}
            shed = priv.get("shed") or {}

            milk_in_shed = int(shed.get("MILK", 0) or 0)
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            has_milk_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "MILK" for o in market_orders)
            has_straw_sell = any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" and o[1] == "STRAWBERRY" for o in market_orders)

            if not has_milk_sell and milk_in_shed >= 2 and len(market_orders) < 5:
                market_orders.append(["SELL", "MILK", milk_in_shed])
                milk_preemptions += 1

            if not has_straw_sell and straw_in_shed >= 4 and len(market_orders) < 5:
                market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                straw_preemptions += 1

        return {
            "farmer": list(act.get("farmer") or ["PASS"]),
            "hands": [list(h) for h in (act.get("hands") or [])],
            "market": market_orders
        }

    return agent, lambda: (milk_preemptions, straw_preemptions)

def dissect_loss_match(seed: int) -> Optional[Dict[str, Any]]:
    apex33_agent, get_preempts = create_apex33_agent()
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, v41_master_agent])
    obs = trainer.reset()

    wealth_curve_our = []
    wealth_curve_opp = []
    step_records = []

    for s in range(720):
        act = apex33_agent(obs)
        farms = obs.get("farms") or []
        priv = obs.get("private") or {}
        shed = priv.get("shed") or {}

        w_our = float(farms[0].get("money", 0.0) or 0.0) if farms else 0.0
        w_opp = float(farms[1].get("money", 0.0) or 0.0) if len(farms) > 1 else 0.0

        wealth_curve_our.append(w_our)
        wealth_curve_opp.append(w_opp)

        prices = (obs.get("market") or {}).get("prices") or {}

        step_records.append({
            "step": s,
            "day": s // 24,
            "mod24": s % 24,
            "our_money": w_our,
            "opp_money": w_opp,
            "our_shed_milk": int(shed.get("MILK", 0) or 0),
            "our_shed_straw": int(shed.get("STRAWBERRY", 0) or 0),
            "our_act": act,
            "prices": prices,
        })

        obs, rew, done, info = trainer.step(act)
        if done:
            break

    w_final_our = float(rew if rew is not None else 0.0)
    farms = obs.get("farms") or []
    w_final_opp = float(farms[1].get("money", 0.0) or 0.0) if len(farms) > 1 else 0.0

    # Only dissect if it's an actual loss
    if w_final_our >= w_final_opp:
        return None

    # Find divergence step T: first step where opp_money - our_money > $1500
    t_divergence = None
    for s in range(len(wealth_curve_our)):
        gap = wealth_curve_opp[s] - wealth_curve_our[s]
        if gap >= 1500.0:
            future_gaps = [wealth_curve_opp[k] - wealth_curve_our[k] for k in range(s, min(s + 24, len(wealth_curve_our)))]
            if all(g > 500.0 for g in future_gaps):
                t_divergence = s
                break

    if t_divergence is None:
        t_divergence = len(wealth_curve_our) // 2

    div_rec = step_records[t_divergence]

    # Analyze root cause
    milk_p, straw_p = get_preempts()

    # Determine cause taxonomy
    if t_divergence <= 120:
        cause = "Early Day 1-5 Capital Squeeze"
    elif 240 <= t_divergence <= 288:
        cause = "Day 10-12 SW Land Race Preemption Deficit"
    elif 400 <= t_divergence <= 456:
        cause = "Day 17-19 First Strawberry Crop Preemption Deficit"
    elif t_divergence >= 600:
        cause = "Day 25-30 Late Game Liquidation Gap"
    else:
        cause = "Mid-Game Capital Reinvestment Lag"

    return {
        "seed": seed,
        "our_final_wealth": w_final_our,
        "opp_final_wealth": w_final_opp,
        "delta": w_final_opp - w_final_our,
        "t_divergence": t_divergence,
        "t_day": t_divergence // 24,
        "t_mod24": t_divergence % 24,
        "cause": cause,
        "milk_at_t": div_rec["our_shed_milk"],
        "straw_at_t": div_rec["our_shed_straw"],
        "our_cash_at_t": div_rec["our_money"],
        "opp_cash_at_t": div_rec["opp_money"],
        "milk_preemptions_total": milk_p,
        "straw_preemptions_total": straw_p,
    }

def run_phase20():
    print("====================================================================================================", flush=True)
    print("🔬 PHASE 20: MICRO-DISSECTION OF THE 13 APEX 3.3 LOSSES (50-SEED TOURNAMENT)", flush=True)
    print("====================================================================================================", flush=True)

    seeds = [70000 + i * 31 for i in range(50)]
    losses_data = []

    for seed in seeds:
        res = dissect_loss_match(seed)
        if res is not None:
            losses_data.append(res)
            print(f"  ❌ Loss Seed {seed}: -${res['delta']:,.2f} | Div Step {res['t_divergence']} (Day {res['t_day']}) | {res['cause']}")

    print(f"\nDissected {len(losses_data)} total losses out of 50 seeds ({len(losses_data)/50*100:.1f}% loss rate).\n")

    cause_counts = defaultdict(int)
    for l in losses_data:
        cause_counts[l["cause"]] += 1

    print("--- 📊 APEX 3.3 LOSS ROOT CAUSE CLUSTERS ---")
    for cause, count in sorted(cause_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(losses_data)) * 100.0 if losses_data else 0.0
        print(f"  {count} matches ({pct:.1f}%): {cause}")

    report_md = f"""# 📜 Phase 20: Micro-Dissection of APEX 3.3 Remaining Losses Report

> **Research Purpose**: Granular turn-by-turn dissection of the **13 exact loss matches** where APEX 3.3 was defeated by V4.1 Master Opponent during the 50-seed Phase 19 tournament.
> **Objective**: Determine whether remaining APEX 3.3 losses stem from a single, fixable mechanism (enabling APEX 3.4) or represent irreducible seed variance.

---

## 📊 1. APEX 3.3 Remaining Loss Taxonomy & Distribution

| Loss Cause Category | Loss Count | % of Losses | Strategic Mechanism |
| :--- | :---: | :---: | :--- |
"""
    for cause, count in sorted(cause_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(losses_data)) * 100.0 if losses_data else 0.0
        report_md += f"| **{cause}** | **{count}** | **{pct:.1f}%** | Specific clearance timing / land race |\n"

    report_md += """
---

## 🔍 2. Granular Seed-by-Seed Dissection (All 13 Losses)

| Seed | APEX 3.3 Wealth ($) | Opponent Wealth ($) | Loss Delta ($) | Divergence ($T$) | Day | Mod 24 | Shed Milk @ T | Shed Straw @ T | Loss Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""
    for l in losses_data:
        report_md += f"| `{l['seed']}` | ${l['our_final_wealth']:,.2f} | ${l['opp_final_wealth']:,.2f} | -${l['delta']:,.2f} | **Step {l['t_divergence']}** | Day {l['t_day']} | `{l['t_mod24']}` | {l['milk_at_t']} | {l['straw_at_t']} | {l['cause']} |\n"

    report_md += """
---

## 💡 3. Key Findings & APEX 3.4 Directive

1. **Failure Mode Pattern Analysis**:
   - Checks if remaining losses are concentrated at Day 10-12 (Pre-SW land) or Day 25-30 (End-game liquidation).

2. **Preemption Threshold Calibration**:
   - Evaluates if Milk preemption threshold (`milk >= 2`) or Strawberry threshold (`straw >= 4`) can be refined.

3. **APEX 3.4 Recommendation**:
   - If a single mechanism causes the majority of the 13 losses, design APEX 3.4; if losses are random seed noise, freeze APEX 3.3 as candidate.
"""

    report_path = os.path.join(BASE_DIR, "docs", "PHASE20_APEX33_LOSS_DISSECTION_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nReport written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_phase20()
