"""PHASE 15: PRODUCTION CAPACITY & WORKER UTILIZATION FORENSICS ENGINE.

Deep comparative forensics across 71 Top-Tier Replays vs 30 V4.1 Simulation Trajectories:
1. 👷 WORKER UTILIZATION & ACTION TAXONOMY:
   - Productive Production Actions (Plant, Harvest, Water, Till, Fertilize, Feed, Care, Milk, Shear, Build)
   - Travel / Movement Actions (North, South, East, West)
   - Idle / Wasted Actions (Pass, None, No-op)
   - Productive Action Ratio = Productive Steps / Total Available Worker Steps (Farmer + Hands)

2. 🐄 ANIMAL ACQUISITION CONDITIONS & TIMING:
   - Exact state when Cow #1, Cow #2, and Cow #3 are purchased:
     - Cash before purchase ($)
     - Active worker count
     - Feed / Wheat inventory
     - Land quadrants unlocked
     - Step / Day of purchase

3. ⏱️ PRODUCTION CYCLE EFFICIENCY & LATENCIES:
   - Feed -> Milk conversion cycle latency
   - Crop harvest -> Replant turnaround downtime (plot vacancy)
   - Cash arrival -> Reinvestment latency (how many steps cash sits idle before being deployed into productive assets)

4. 📊 PRODUCTIVE CAPACITY BOTTLENECK IDENTIFICATION:
   - Revealing the exact causal differences between Top-Tier Champions and V4.1 Baseline.

Outputs: docs/PHASE15_PRODUCTION_CAPACITY_REPORT.md
"""

from __future__ import annotations
import sys
import os
import glob
import json
import math
import copy
import importlib
import importlib.util
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

PRODUCTIVE_VERBS = {
    "PLANT", "HARVEST", "WATER", "TILL", "FERTILIZE", "FEED",
    "MILK", "CARE", "SHEAR", "COLLECT", "COLLECT_EGG",
    "BUILD_COOP", "BUILD_BARN", "BUILD_PASTURE", "PICKUP", "PLACE"
}

TRAVEL_VERBS = {"NORTH", "SOUTH", "EAST", "WEST"}

IDLE_VERBS = {"PASS", "NONE", "NOOP", "IDLE"}

def classify_action(act: Any) -> str:
    """Classifies a worker action into 'productive', 'travel', or 'idle'."""
    if not act:
        return "idle"
    if isinstance(act, str):
        verb = act.strip().upper()
    elif isinstance(act, (list, tuple)) and len(act) > 0:
        verb = str(act[0]).strip().upper()
    else:
        return "idle"

    if verb in PRODUCTIVE_VERBS:
        return "productive"
    elif verb in TRAVEL_VERBS:
        return "travel"
    elif verb in IDLE_VERBS:
        return "idle"
    return "other"

def analyze_worker_timeline(steps: List[Any], agent_idx: int) -> Dict[str, Any]:
    """Extracts detailed worker utilization, cow acquisition conditions, and production cycles."""
    timeline = {
        "final_wealth": 0.0,
        "total_worker_turns": 0,
        "farmer_turns": 0,
        "hands_turns": 0,
        "actions_breakdown": {
            "productive": 0,
            "travel": 0,
            "idle": 0,
            "other": 0,
        },
        "productive_by_type": defaultdict(int),
        "cow_purchases": [],
        "sheep_purchases": [],
        "reinvestment_latencies": [],
        "cash_trajectory": [],
        "workers_trajectory": [],
    }

    if not steps or len(steps) < 2:
        return timeline

    final_step = steps[-1]
    if len(final_step) > agent_idx:
        timeline["final_wealth"] = float(final_step[agent_idx].get("reward", 0.0) or 0.0)

    last_large_cash_inflow_step = None
    cow_count_tracker = 0

    for step_idx, step in enumerate(steps):
        if len(step) <= agent_idx:
            continue

        agent_data = step[agent_idx]
        action = agent_data.get("action") or {}
        obs = agent_data.get("observation") or {}
        farms = obs.get("farms") or []
        farm = farms[agent_idx] if len(farms) > agent_idx else {}
        cash = float(farm.get("money", 0.0) or 0.0)
        unlocked = farm.get("unlocked_quadrants") or ["NW"]
        hands = farm.get("hands") or []
        num_workers = len(hands) + 1

        priv = obs.get("private") or {}
        shed = priv.get("shed") or {}
        wheat_feed = shed.get("WHEAT", 0)
        milk_in_shed = shed.get("MILK", 0)

        timeline["cash_trajectory"].append(cash)
        timeline["workers_trajectory"].append(num_workers)

        # 1. Analyze Farmer action
        farmer_act = action.get("farmer")
        cat_farmer = classify_action(farmer_act)
        timeline["farmer_turns"] += 1
        timeline["total_worker_turns"] += 1
        timeline["actions_breakdown"][cat_farmer] += 1
        if cat_farmer == "productive" and isinstance(farmer_act, (list, tuple)) and len(farmer_act) > 0:
            timeline["productive_by_type"][str(farmer_act[0]).upper()] += 1

        # 2. Analyze Hired Hands actions
        hands_acts = action.get("hands") or []
        for h_act in hands_acts:
            cat_hand = classify_action(h_act)
            timeline["hands_turns"] += 1
            timeline["total_worker_turns"] += 1
            timeline["actions_breakdown"][cat_hand] += 1
            if cat_hand == "productive" and isinstance(h_act, (list, tuple)) and len(h_act) > 0:
                timeline["productive_by_type"][str(h_act[0]).upper()] += 1

        # 3. Market Purchases (Cow condition extraction & Reinvestment tracking)
        market_actions = action.get("market") or []
        for m_act in market_actions:
            if isinstance(m_act, (list, tuple)) and len(m_act) >= 2:
                m_type = m_act[0]
                m_item = m_act[1]
                m_qty = int(m_act[2]) if len(m_act) > 2 else 1

                if m_type == "BUY_ANIMAL" and m_item == "COW":
                    cow_count_tracker += 1
                    timeline["cow_purchases"].append({
                        "cow_index": cow_count_tracker,
                        "step": step_idx,
                        "day": step_idx // 24,
                        "cash_before": cash,
                        "workers_count": num_workers,
                        "feed_inventory": wheat_feed,
                        "milk_inventory": milk_in_shed,
                        "quadrants_count": len(unlocked),
                    })

                elif m_type == "BUY_ANIMAL" and m_item == "SHEEP":
                    timeline["sheep_purchases"].append({
                        "step": step_idx,
                        "day": step_idx // 24,
                        "cash_before": cash,
                        "workers_count": num_workers,
                    })

                elif m_type == "SELL" and cash < 100.0:
                    # Inflow event
                    last_large_cash_inflow_step = step_idx

                if m_type in ["BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE"] and last_large_cash_inflow_step is not None:
                    latency = step_idx - last_large_cash_inflow_step
                    timeline["reinvestment_latencies"].append(latency)
                    last_large_cash_inflow_step = None

    return timeline

def run_phase15_forensics():
    print("====================================================================================================", flush=True)
    print("🔬 PHASE 15: PRODUCTION CAPACITY & WORKER UTILIZATION FORENSICS ENGINE", flush=True)
    print("====================================================================================================", flush=True)

    # 1. Load Replays
    replay_files = glob.glob(os.path.join(BASE_DIR, "**", "*.json"), recursive=True)
    valid_replays = [f for f in replay_files if "reviews" in f and os.path.getsize(f) > 50000]
    print(f"Loaded {len(valid_replays)} top-tier replay files from review corpus.")

    top_tier_timelines: List[Dict[str, Any]] = []
    replays_loss_timelines: List[Dict[str, Any]] = []

    for fpath in valid_replays:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                d = json.load(f)
            steps = d.get("steps", [])
            rewards = d.get("rewards", [0.0, 0.0])
            if not steps or len(steps) < 100:
                continue

            r0 = float(rewards[0] or 0.0)
            r1 = float(rewards[1] or 0.0)

            t0 = analyze_worker_timeline(steps, 0)
            t1 = analyze_worker_timeline(steps, 1)

            if r0 > r1 and r0 >= 60000:
                top_tier_timelines.append(t0)
                replays_loss_timelines.append(t1)
            elif r1 > r0 and r1 >= 60000:
                top_tier_timelines.append(t1)
                replays_loss_timelines.append(t0)
        except Exception:
            continue

    # 2. Run V4.1 Baseline Simulation Trajectories across 30 seeds under 24-step parity
    print("\nSimulating 30 V4.1 baseline matches under Kaggle 24-step parity...", flush=True)
    v41_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("v41_mod", v41_path)
    v41_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v41_mod)
    v41_agent = v41_mod.agent

    v41_timelines: List[Dict[str, Any]] = []
    for seed_idx in range(30):
        seed = 42000 + seed_idx * 17
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
        trainer = env.train([None, v41_agent])
        obs = trainer.reset()

        steps_record = []
        for s in range(720):
            act = v41_agent(obs)
            # Record step in replay format: [[{"observation": obs, "action": act}], ...]
            step_entry = [{"observation": obs, "action": act}, {}]
            steps_record.append(step_entry)
            obs, rew, done, info = trainer.step(act)
            if done:
                break
        final_entry = [{"observation": obs, "reward": rew}, {}]
        steps_record.append(final_entry)

        t_v41 = analyze_worker_timeline(steps_record, 0)
        v41_timelines.append(t_v41)

    print(f"Analyzed: {len(top_tier_timelines)} Top-Tier Champions vs {len(v41_timelines)} V4.1 Simulations.", flush=True)

    # 3. Compute Aggregate Statistics
    def compute_summary(timelines: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(timelines)
        if n == 0:
            return {}
        
        avg_wealth = sum(t["final_wealth"] for t in timelines) / n
        avg_worker_turns = sum(t["total_worker_turns"] for t in timelines) / n
        
        prod_ratio = sum(t["actions_breakdown"]["productive"] / max(1, t["total_worker_turns"]) for t in timelines) / n * 100.0
        travel_ratio = sum(t["actions_breakdown"]["travel"] / max(1, t["total_worker_turns"]) for t in timelines) / n * 100.0
        idle_ratio = sum(t["actions_breakdown"]["idle"] / max(1, t["total_worker_turns"]) for t in timelines) / n * 100.0

        # Cow purchases summary
        cow1_steps = [p["step"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 1]
        cow2_steps = [p["step"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 2]
        cow3_steps = [p["step"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 3]

        cow1_cash = [p["cash_before"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 1]
        cow2_cash = [p["cash_before"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 2]
        cow3_cash = [p["cash_before"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 3]

        cow1_workers = [p["workers_count"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 1]
        cow2_workers = [p["workers_count"] for t in timelines for p in t["cow_purchases"] if p["cow_index"] == 2]

        all_latencies = [lat for t in timelines for lat in t["reinvestment_latencies"]]
        avg_latency = sum(all_latencies) / max(1, len(all_latencies)) if all_latencies else 0.0

        # Action breakdown by type
        all_verbs = defaultdict(int)
        for t in timelines:
            for v, count in t["productive_by_type"].items():
                all_verbs[v] += count

        return {
            "count": n,
            "avg_wealth": avg_wealth,
            "avg_worker_turns": avg_worker_turns,
            "productive_ratio": prod_ratio,
            "travel_ratio": travel_ratio,
            "idle_ratio": idle_ratio,
            "cow1_step": sum(cow1_steps) / max(1, len(cow1_steps)) if cow1_steps else None,
            "cow2_step": sum(cow2_steps) / max(1, len(cow2_steps)) if cow2_steps else None,
            "cow3_step": sum(cow3_steps) / max(1, len(cow3_steps)) if cow3_steps else None,
            "cow1_cash": sum(cow1_cash) / max(1, len(cow1_cash)) if cow1_cash else None,
            "cow2_cash": sum(cow2_cash) / max(1, len(cow2_cash)) if cow2_cash else None,
            "cow3_cash": sum(cow3_cash) / max(1, len(cow3_cash)) if cow3_cash else None,
            "cow1_workers": sum(cow1_workers) / max(1, len(cow1_workers)) if cow1_workers else None,
            "cow2_workers": sum(cow2_workers) / max(1, len(cow2_workers)) if cow2_workers else None,
            "reinvestment_latency": avg_latency,
            "verbs": {k: v / n for k, v in sorted(all_verbs.items(), key=lambda x: x[1], reverse=True)},
        }

    top_summary = compute_summary(top_tier_timelines)
    v41_summary = compute_summary(v41_timelines)
    loss_summary = compute_summary(replays_loss_timelines)

    print("\n--- 📊 SUMMARY METRICS ---")
    print(f"Top-Tier Avg Wealth: ${top_summary.get('avg_wealth', 0):,.2f} | V4.1 Avg Wealth: ${v41_summary.get('avg_wealth', 0):,.2f}")
    print(f"Productive Ratio: Top {top_summary.get('productive_ratio', 0):.2f}% vs V4.1 {v41_summary.get('productive_ratio', 0):.2f}%")
    print(f"Travel Ratio:     Top {top_summary.get('travel_ratio', 0):.2f}% vs V4.1 {v41_summary.get('travel_ratio', 0):.2f}%")
    print(f"Idle Ratio:       Top {top_summary.get('idle_ratio', 0):.2f}% vs V4.1 {v41_summary.get('idle_ratio', 0):.2f}%")
    print(f"Cow #1 Step:      Top {top_summary.get('cow1_step', 0)} vs V4.1 {v41_summary.get('cow1_step', 0)}")
    print(f"Cow #2 Step:      Top {top_summary.get('cow2_step', 0)} vs V4.1 {v41_summary.get('cow2_step', 0)}")
    print(f"Cow #2 Cash:      Top ${top_summary.get('cow2_cash', 0):,.2f} vs V4.1 ${v41_summary.get('cow2_cash', 0):,.2f}")
    print(f"Cow #2 Workers:   Top {top_summary.get('cow2_workers', 0):.1f} vs V4.1 {v41_summary.get('cow2_workers', 0):.1f}")
    print(f"Reinvestment Lat: Top {top_summary.get('reinvestment_latency', 0):.2f} steps vs V4.1 {v41_summary.get('reinvestment_latency', 0):.2f} steps")

    # Generate Markdown Report
    report_md = f"""# 📜 Phase 15: Production Capacity & Worker Utilization Forensics Report

> **Research Purpose**: Granular deconstruction of worker time budgets, animal acquisition conditions, and production cycle latencies across **71 Top-Tier Replays** vs **30 V4.1 Master Trajectories** under 24-step parity.
> **Objective**: Identify the true causal source of top-tier productive superiority without fighting the liquidity mechanics.

---

## 📊 1. Worker Utilization & Action Taxonomy Breakdown

| Utilization Metric | Top-Tier Winning Champions (71 Replays) | V4.1 Master Baseline (30 Seeds) | Replay Defeated Opponents | Delta (Top vs V4.1) |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Final Wealth ($)** | **${top_summary.get('avg_wealth', 0):,.2f}** | ${v41_summary.get('avg_wealth', 0):,.2f} | ${loss_summary.get('avg_wealth', 0):,.2f} | **+${top_summary.get('avg_wealth', 0) - v41_summary.get('avg_wealth', 0):,.2f}** |
| **Total Worker Turns** | {top_summary.get('avg_worker_turns', 0):,.1f} | {v41_summary.get('avg_worker_turns', 0):,.1f} | {loss_summary.get('avg_worker_turns', 0):,.1f} | {top_summary.get('avg_worker_turns', 0) - v41_summary.get('avg_worker_turns', 0):+.1f} |
| **Productive Action Ratio** | **{top_summary.get('productive_ratio', 0):.2f}%** | {v41_summary.get('productive_ratio', 0):.2f}% | {loss_summary.get('productive_ratio', 0):.2f}% | **{top_summary.get('productive_ratio', 0) - v41_summary.get('productive_ratio', 0):+.2f}%** |
| **Travel / Walking Ratio** | {top_summary.get('travel_ratio', 0):.2f}% | {v41_summary.get('travel_ratio', 0):.2f}% | {loss_summary.get('travel_ratio', 0):.2f}% | {top_summary.get('travel_ratio', 0) - v41_summary.get('travel_ratio', 0):+.2f}% |
| **Idle / Wasted Ratio** | **{top_summary.get('idle_ratio', 0):.2f}%** | {v41_summary.get('idle_ratio', 0):.2f}% | {loss_summary.get('idle_ratio', 0):.2f}% | **{top_summary.get('idle_ratio', 0) - v41_summary.get('idle_ratio', 0):+.2f}%** |
| **Reinvestment Latency** | **{top_summary.get('reinvestment_latency', 0):.2f} steps** | {v41_summary.get('reinvestment_latency', 0):.2f} steps | {loss_summary.get('reinvestment_latency', 0):.2f} steps | **{top_summary.get('reinvestment_latency', 0) - v41_summary.get('reinvestment_latency', 0):+.2f} steps** |

---

## 🐄 2. Animal Acquisition State Conditions

| Acquisition Event | Top-Tier Step | V4.1 Step | Top Cash Before ($) | V4.1 Cash Before ($) | Top Workers | V4.1 Workers |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cow #1 Acquisition** | Step {top_summary.get('cow1_step', 0):.1f} | Step {v41_summary.get('cow1_step', 0):.1f} | ${top_summary.get('cow1_cash', 0):,.2f} | ${v41_summary.get('cow1_cash', 0):,.2f} | {top_summary.get('cow1_workers', 0):.1f} | {v41_summary.get('cow1_workers', 0):.1f} |
| **Cow #2 Acquisition** | Step {top_summary.get('cow2_step', 0):.1f} | Step {v41_summary.get('cow2_step', 0):.1f} | ${top_summary.get('cow2_cash', 0):,.2f} | ${v41_summary.get('cow2_cash', 0):,.2f} | {top_summary.get('cow2_workers', 0):.1f} | {v41_summary.get('cow2_workers', 0):.1f} |
| **Cow #3 Acquisition** | Step {top_summary.get('cow3_step', 0) if top_summary.get('cow3_step') else 'N/A'} | N/A | ${top_summary.get('cow3_cash', 0) if top_summary.get('cow3_cash') else 0:,.2f} | N/A | N/A | N/A |

---

## 🌾 3. Productive Verb Distribution (Average Actions per Episode)

| Action Verb | Top-Tier Champions | V4.1 Master Baseline | Delta |
| :--- | :---: | :---: | :---: |
"""
    verbs_top = top_summary.get("verbs", {})
    verbs_v41 = v41_summary.get("verbs", {})
    all_keys = set(verbs_top.keys()).union(set(verbs_v41.keys()))
    for verb in sorted(all_keys, key=lambda x: verbs_top.get(x, 0), reverse=True):
        c_top = verbs_top.get(verb, 0.0)
        c_v41 = verbs_v41.get(verb, 0.0)
        report_md += f"| **{verb}** | {c_top:.1f} | {c_v41:.1f} | {c_top - c_v41:+.1f} |\n"

    report_md += f"""
---

## 🔍 4. Key Causal Takeaways

1. **Worker Utilization Discrepancy**:
   - Compares the ratio of productive actions (tilling, planting, harvesting, feeding, care) versus spatial travel steps.
   - Shows where travel routing inefficiencies drain valuable worker cycles.

2. **Cow #2 Acquisition State Frontier**:
   - Reveals the exact state envelope (Cash, Workers, Feed) under which winning agents transition from 1 cow to 2 cows.

3. **Reinvestment Velocity**:
   - Measures how immediately cash proceeds are redeployed into revenue-generating inputs (seeds, feed, labor).
"""

    report_path = os.path.join(BASE_DIR, "docs", "PHASE15_PRODUCTION_CAPACITY_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nReport written to: {report_path}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_phase15_forensics()
