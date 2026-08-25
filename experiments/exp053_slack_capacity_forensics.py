"""EXP053: Track B (Slack Capacity Forensics & Labor Surplus Mapping).
Analyzes step-level worker utilization, idle steps, and surplus capacity across all 64 matches on 32 holdout seeds.
Measures for every step t in [0, 720]:
1. Worker Task Allocation:
   - Critical Core Tasks: TILL, PLANT, WATER, HARVEST, MILK, FEED, DEPOSIT
   - Transit / Movement Steps: MOVE_TO
   - Pure Idle Steps: PASS / No assigned task
2. Slack Metrics:
   - Total Worker-Steps Available: 13 workers * 720 steps = 9,360 worker-steps/match
   - Total Worker-Steps Utilized vs Total Idle Worker-Steps
   - Slack Heatmap by Day (Days 0-29)
3. Evaluates whether actionable surplus capacity exists for a zero-drag Slack-Sidecar Engine.
"""
from __future__ import annotations
import sys
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

def audit_match_slack(seed: int) -> list[dict]:
    """Traces worker task breakdown on a single seed across both seats."""
    results = []

    for seat in [0, 1]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        agent_d1 = VariantDAgent()

        step = 0
        total_worker_steps = 0
        active_worker_steps = 0
        move_worker_steps = 0
        idle_worker_steps = 0
        daily_idle = [0] * 30
        daily_total = [0] * 30

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            if seat == 0:
                act = agent_d1.act(obs0, env.configuration)
                opp_act = bot_v18.agent(obs1)
                env.step([act, opp_act])
            else:
                opp_act = bot_v18.agent(obs0)
                act = agent_d1.act(obs1, env.configuration)
                env.step([opp_act, act])

            day = min(29, step // 24)

            # Analyze actions executed by farmer & hands
            farmer_cmd = act.get("farmer") if isinstance(act, dict) else ["PASS"]
            hands_cmds = act.get("hands") if isinstance(act, dict) else []

            all_units = [farmer_cmd] + list(hands_cmds or [])
            for cmd in all_units:
                total_worker_steps += 1
                daily_total[day] += 1
                c_type = cmd[0] if (isinstance(cmd, (list, tuple)) and len(cmd) > 0) else "PASS"

                if c_type == "PASS":
                    idle_worker_steps += 1
                    daily_idle[day] += 1
                elif c_type in ("MOVE_TO", "MOVE"):
                    move_worker_steps += 1
                else:
                    # Productive: TILL, PLANT, WATER, HARVEST, MILK, FEED, STORE, PICKUP, BUY
                    active_worker_steps += 1

            step += 1

        final_bank = float(env.state[seat].reward or 0.0)
        opp_bank = float(env.state[1 - seat].reward or 0.0)

        results.append({
            "seed": seed,
            "seat": seat,
            "d1_bank": final_bank,
            "opp_bank": opp_bank,
            "is_win": final_bank > opp_bank,
            "total_worker_steps": total_worker_steps,
            "active_worker_steps": active_worker_steps,
            "move_worker_steps": move_worker_steps,
            "idle_worker_steps": idle_worker_steps,
            "slack_pct": (idle_worker_steps / total_worker_steps * 100.0) if total_worker_steps > 0 else 0.0,
            "daily_idle": daily_idle,
            "daily_total": daily_total,
        })

    return results

def run_exp053():
    print("=" * 105)
    print("EXP053: SLACK CAPACITY FORENSICS & LABOR SURPLUS MAPPING (64 MATCHES / 32 SEEDS)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel step-level worker telemetry audit across 64 matches...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(audit_match_slack, seeds))

    all_audits = [m for sub in nested_res for m in sub]

    total_steps = sum(a["total_worker_steps"] for a in all_audits)
    active_steps = sum(a["active_worker_steps"] for a in all_audits)
    move_steps = sum(a["move_worker_steps"] for a in all_audits)
    idle_steps = sum(a["idle_worker_steps"] for a in all_audits)

    active_pct = (active_steps / total_steps) * 100.0
    move_pct = (move_steps / total_steps) * 100.0
    idle_pct = (idle_steps / total_steps) * 100.0

    print("\n" + "=" * 105)
    print("1. GLOBAL POPULATION LABOR ALLOCATION BREAKDOWN (Across 64 Matches / 599,040 Worker-Steps)")
    print("=" * 105)
    print(f"{'Worker Activity Category':<35} | {'Total Worker-Steps':>18} | {'% of Total Capacity':>22} | {'Physical Role'}")
    print("-" * 105)
    print(f"{'Productive Field Tasks (Active)':<35} | {active_steps:>18,d} | {active_pct:>21.2f}% | Till, Plant, Water, Harvest, Milk, Feed")
    print(f"{'Transit & Navigation (Moving)':<35} | {move_steps:>18,d} | {move_pct:>21.2f}% | Walking between plots, shed, & pasture")
    print(f"{'Pure Idle Capacity (PASS)':<35} | {idle_steps:>18,d} | {idle_pct:>21.2f}% | Unused / Waiting without assigned task")
    print("-" * 105)
    print(f"{'Total Worker Capacity':<35} | {total_steps:>18,d} | {100.0:>21.2f}% | 13 Workers * 720 Steps")
    print("=" * 105)

    # 2. Daily Slack Heatmap across 30 Days
    agg_daily_idle = [sum(a["daily_idle"][d] for a in all_audits) for d in range(30)]
    agg_daily_total = [sum(a["daily_total"][d] for a in all_audits) for d in range(30)]
    daily_slack_pct = [(agg_daily_idle[d] / agg_daily_total[d] * 100.0) if agg_daily_total[d] > 0 else 0.0 for d in range(30)]

    print("\n" + "=" * 105)
    print("2. TEMPORAL SLACK HEATMAP (Idle Capacity by Game Phase)")
    print("=" * 105)
    print(f"{'Game Phase (Days)':<28} | {'Avg Worker Count':>16} | {'Daily Idle Steps':>18} | {'Daily Total Steps':>18} | {'Slack %':>10}")
    print("-" * 105)

    phases = [
        ("Opening (Days 0-4)", range(0, 5)),
        ("Expansion (Days 5-9)", range(5, 10)),
        ("Early Saturated (Days 10-14)", range(10, 15)),
        ("Peak Production (Days 15-19)", range(15, 20)),
        ("Late Waves (Days 20-24)", range(20, 25)),
        ("Endgame / Clearance (Days 25-29)", range(25, 30)),
    ]

    for p_name, d_range in phases:
        p_idle = sum(agg_daily_idle[d] for d in d_range)
        p_tot = sum(agg_daily_total[d] for d in d_range)
        p_slack = (p_idle / p_tot * 100.0) if p_tot > 0 else 0.0
        avg_w = (p_tot / (len(d_range) * 24 * len(all_audits)))
        print(f"{p_name:<28} | {avg_w:>16.1f} | {p_idle:>18,d} | {p_tot:>18,d} | {p_slack:>9.2f}%")

    print("=" * 105)

    # Forensic Verdict
    print("\n3. FORENSIC CAPACITY VERDICT:")
    if idle_pct < 5.0:
        print(f"  - System Saturation Level : 95%+ Saturated (Only {idle_pct:.2f}% Idle Capacity across the entire game)")
        print("  - Side-Car Feasibility    : UNFEASIBLE. Worker labor is virtually 100% committed to core strawberry/dairy tasks.")
    elif idle_pct < 15.0:
        print(f"  - System Saturation Level : Moderately Saturated ({idle_pct:.2f}% Idle Capacity in localized pockets)")
        print("  - Side-Car Feasibility    : Micro-burst optimization only. No sustained side-car projects.")
    else:
        print(f"  - System Saturation Level : Substantial Slack ({idle_pct:.2f}% Idle Capacity)")
        print("  - Side-Car Feasibility    : HIGH. Actionable surplus capacity available for side-car engine.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp053()
