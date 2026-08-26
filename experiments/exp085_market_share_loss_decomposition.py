"""EXP085: Competitive Market-Share Loss Decomposition.

Analyzes all 20 live tournament losses of Variant D.1 (Ref 55780289):
Decomposes each match across critical macro-milestones:
- Day 8 (Step 192)
- Day 12 (Step 288)
- Day 15 (Step 360)
- Day 20 (Step 480)
- Day 25 (Step 600)
- Day 27 (Step 648)
- Day 29 (Step 696)
- Step 719 (Terminal Execution Boundary)

Classifies every loss into one of four causal buckets:
- Bucket A: Market Share Loss (D.1 Volume Share < 50%)
- Bucket B: Price Realization Loss (Realized $/unit D.1 < Opponent)
- Bucket C: Commodity Composition Loss (Opponent dairy/other revenue edge)
- Bucket D: Symmetric Parity / Settlement Loss (Both within 2% parity, decided by terminal settlement)
"""
from __future__ import annotations
import sys
import os
import json
import glob
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

SUMMARY_PATH = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches", "d1_telemetry_summary.json")

def load_live_losses():
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("losses", [])

CHECKPOINTS = [192, 288, 360, 480, 600, 648, 696, 719]

def decompose_loss_match(loss_info):
    seed = loss_info.get("seed")
    if seed is None:
        return None

    # Determine seat
    our_seat = loss_info.get("our_seat", 0)
    opp_seat = 1 - our_seat

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    agent_d1 = VariantDAgent()

    p0_straw_rev = 0.0
    p1_straw_rev = 0.0
    p0_milk_rev = 0.0
    p1_milk_rev = 0.0
    p0_other_rev = 0.0
    p1_other_rev = 0.0

    p0_straw_qty = 0
    p1_straw_qty = 0
    p0_milk_qty = 0
    p1_milk_qty = 0

    step_num = 0
    snapshots = {}

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        market = obs0.get("market", {})
        prices = market.get("prices", {}) if isinstance(market, dict) else {}
        sp = float(prices.get("STRAWBERRY", prices.get(1, 0.0)) if isinstance(prices, dict) else 0.0)
        mp = float(prices.get("MILK", prices.get(4, 0.0)) if isinstance(prices, dict) else 0.0)

        if our_seat == 0:
            act0 = agent_d1.act(obs0, env.configuration)
            act1 = bot_v18.agent(obs1)
            d1_act = act0
            opp_act = act1
        else:
            act0 = bot_v18.agent(obs0)
            act1 = agent_d1.act(obs1, env.configuration)
            d1_act = act1
            opp_act = act0

        # Track sell executions
        if isinstance(d1_act, dict) and "market" in d1_act:
            for m in d1_act["market"]:
                if len(m) >= 3 and m[0] == "SELL":
                    qty = m[2]
                    if m[1] == "STRAWBERRY":
                        p0_straw_qty += qty
                        p0_straw_rev += qty * sp
                    elif m[1] == "MILK":
                        p0_milk_qty += qty
                        p0_milk_rev += qty * mp
                    else:
                        p0_other_rev += qty * float(prices.get(m[1], 0.0))

        if isinstance(opp_act, dict) and "market" in opp_act:
            for m in opp_act["market"]:
                if len(m) >= 3 and m[0] == "SELL":
                    qty = m[2]
                    if m[1] == "STRAWBERRY":
                        p1_straw_qty += qty
                        p1_straw_rev += qty * sp
                    elif m[1] == "MILK":
                        p1_milk_qty += qty
                        p1_milk_rev += qty * mp
                    else:
                        p1_other_rev += qty * float(prices.get(m[1], 0.0))

        env.step([act0, act1])
        step_num += 1

        if step_num in CHECKPOINTS:
            cur_obs = env.state[our_seat].observation
            farms = cur_obs.get("farms", [])
            f0 = farms[our_seat] if len(farms) > our_seat else {}
            f1 = farms[opp_seat] if len(farms) > opp_seat else {}
            snapshots[step_num] = {
                "d1_money": float(f0.get("money", 0.0)),
                "opp_money": float(f1.get("money", 0.0)),
                "margin": float(f0.get("money", 0.0)) - float(f1.get("money", 0.0)),
                "straw_price": sp,
            }

    d1_final = float(env.state[our_seat].reward or 0.0)
    opp_final = float(env.state[opp_seat].reward or 0.0)
    total_pie = d1_final + opp_final

    d1_avg_sp = p0_straw_rev / p0_straw_qty if p0_straw_qty > 0 else 0.0
    opp_avg_sp = p1_straw_rev / p1_straw_qty if p1_straw_qty > 0 else 0.0

    # Bucket classification
    price_delta = d1_avg_sp - opp_avg_sp
    volume_delta = p0_straw_qty - p1_straw_qty
    milk_rev_delta = p0_milk_rev - p1_milk_rev
    margin_pct = abs(d1_final - opp_final) / total_pie if total_pie > 0 else 0.0

    if volume_delta < -20:
        bucket = "Bucket A: Market Share (Volume Loss)"
    elif price_delta < -5.0:
        bucket = "Bucket B: Price Realization Loss"
    elif milk_rev_delta < -5000:
        bucket = "Bucket C: Commodity Composition Loss"
    else:
        bucket = "Bucket D: Symmetrical Parity / Settlement Variance"

    return {
        "ep_id": loss_info.get("ep_id"),
        "seed": seed,
        "opp_sub": loss_info.get("opp_sub_id"),
        "opp_elo": loss_info.get("opp_score_init", 0.0),
        "real_margin": loss_info.get("margin", 0.0),
        "sim_d1": d1_final,
        "sim_opp": opp_final,
        "sim_margin": d1_final - opp_final,
        "total_pie": total_pie,
        "d1_share": d1_final / total_pie if total_pie > 0 else 0.0,
        "p0_straw_qty": p0_straw_qty,
        "p1_straw_qty": p1_straw_qty,
        "d1_avg_sp": d1_avg_sp,
        "opp_avg_sp": opp_avg_sp,
        "bucket": bucket,
        "snapshots": snapshots,
    }

def run_exp085():
    print("=" * 105)
    print("EXP085: COMPETITIVE MARKET-SHARE LOSS DECOMPOSITION (20 LIVE LOSSES)")
    print("=" * 105)

    losses = load_live_losses()
    print(f"Loaded {len(losses)} live defeat episodes for macro-decomposition.")

    results = []
    for idx, l in enumerate(losses):
        print(f"[{idx+1}/{len(losses)}] Decomposing Loss Episode {l.get('ep_id')} (Seed: {l.get('seed')}, Opp: {l.get('opp_sub_id')})...", flush=True)
        res = decompose_loss_match(l)
        if res:
            results.append(res)

    print("\n" + "=" * 105)
    print("1. LIVE LOSS MATCH TAXONOMY & FOUR-BUCKET CLASSIFICATION TABLE")
    print("=" * 105)
    print(f"{'Ep ID':<10} | {'Seed':<11} | {'Opp Elo':>8} | {'Real Margin':>12} | {'Total Pie':>11} | {'D.1 Share':>10} | {'Price Edge':>11} | {'Classification'}")
    print("-" * 105)

    for r in results:
        p_edge = r["d1_avg_sp"] - r["opp_avg_sp"]
        print(f"{r['ep_id']:<10} | {r['seed']:<11} | {r['opp_elo']:>8.1f} | ${r['real_margin']:>11,.0f} | ${r['total_pie']:>10,.0f} | {r['d1_share']:>9.1%} | ${p_edge:>+10.2f} | {r['bucket']}")

    print("=" * 105)

    # Bucket Distribution Breakdown
    bucket_counts = {}
    for r in results:
        b = r["bucket"]
        bucket_counts[b] = bucket_counts.get(b, 0) + 1

    print("\n2. LOSS CLUSTER DISTRIBUTION:")
    print("-" * 105)
    for b, count in sorted(bucket_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  • {b:<55}: {count:>2} / {len(results)} matches ({count/len(results):.1%})")

    print("=" * 105)

if __name__ == "__main__":
    run_exp085()
