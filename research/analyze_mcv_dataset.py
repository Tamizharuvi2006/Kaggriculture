"""APEX 3.0: Empirical MCV Dataset Analyzer.
Analyzes mcv_replay_dataset.json to evaluate the empirical downstream wealth deltas
of market actions (SELL WHEAT, SELL FERTILIZER, etc.) conditioned on state features.
"""

from __future__ import annotations
import sys
import os
import json
from collections import defaultdict
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def analyze_mcv_dataset():
    data_path = os.path.join(BASE_DIR, "mcv_replay_dataset.json")
    if not os.path.exists(data_path):
        print(f"Error: Dataset file not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        tuples = json.load(f)

    print("==================================================================================", flush=True)
    print("🟣 APEX 3.0: EMPIRICAL MCV DATASET ANALYSIS REPORT", flush=True)
    print("==================================================================================", flush=True)
    print(f"Total Tuples Analyzed: {len(tuples)}", flush=True)

    # 1. Action Breakdown
    actions_by_item = defaultdict(list)
    for t in tuples:
        m_acts = t.get("executed_market_action", [])
        if not m_acts:
            continue
        for act in m_acts:
            if len(act) >= 3 and act[0] == "SELL":
                item = act[1]
                qty = act[2]
                actions_by_item[item].append((t, qty))

    print(f"\n--- 📊 SELL ACTIONS BY COMMODITY ---", flush=True)
    for item, item_tuples in sorted(actions_by_item.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(item_tuples)
        mean_24 = sum(t[0]["downstream_wealth_24"] - t[0]["cash"] for t in item_tuples) / count
        mean_120 = sum(t[0]["downstream_wealth_120"] - t[0]["cash"] for t in item_tuples) / count
        mean_final = sum(t[0]["final_wealth"] for t in item_tuples) / count
        win_rate = sum(1 for t in item_tuples if t[0]["won_match"]) / count * 100.0
        print(f"  Item: {item:<12} | Count: {count:4d} | Mean Δ24 Steps: +${mean_24:6.2f} | Mean Δ120 Steps: +${mean_120:7.2f} | Win Rate: {win_rate:5.1f}% | Mean Final Wealth: ${mean_final:,.2f}")

    # 2. Conditioned Analysis: WHEAT Selling by Cash State
    wheat_sells = actions_by_item.get("WHEAT", [])
    if wheat_sells:
        print(f"\n--- 🌾 WHEAT SELLING: STATE-CONDITIONED ELASTICITY ---", flush=True)
        low_cash = [t for t, q in wheat_sells if t["cash"] < 300.0]
        med_cash = [t for t, q in wheat_sells if 300.0 <= t["cash"] < 1500.0]
        high_cash = [t for t, q in wheat_sells if t["cash"] >= 1500.0]

        for label, group in [("Low Cash (< $300)", low_cash), ("Med Cash ($300-$1.5k)", med_cash), ("High Cash (> $1.5k)", high_cash)]:
            if not group:
                continue
            cnt = len(group)
            m24 = sum(t["downstream_wealth_24"] - t["cash"] for t in group) / cnt
            m120 = sum(t["downstream_wealth_120"] - t["cash"] for t in group) / cnt
            wr = sum(1 for t in group if t["won_match"]) / cnt * 100.0
            print(f"  [{label:<22}] Count: {cnt:4d} | Mean Δ24: +${m24:6.2f} | Mean Δ120: +${m120:7.2f} | Win Rate: {wr:5.1f}%")

    # 3. Conditioned Analysis: FERTILIZER Selling Dynamics
    fert_sells = actions_by_item.get("FERTILIZER", [])
    if fert_sells:
        print(f"\n--- 🧪 FERTILIZER SELLING: STATE-CONDITIONED ELASTICITY ---", flush=True)
        early_game = [t for t, q in fert_sells if t["step"] < 200]
        mid_game = [t for t, q in fert_sells if 200 <= t["step"] < 500]
        late_game = [t for t, q in fert_sells if t["step"] >= 500]

        for label, group in [("Early Game (Step < 200)", early_game), ("Mid Game (Step 200-500)", mid_game), ("Late Game (Step >= 500)", late_game)]:
            if not group:
                continue
            cnt = len(group)
            m24 = sum(t["downstream_wealth_24"] - t["cash"] for t in group) / cnt
            m120 = sum(t["downstream_wealth_120"] - t["cash"] for t in group) / cnt
            wr = sum(1 for t in group if t["won_match"]) / cnt * 100.0
            print(f"  [{label:<22}] Count: {cnt:4d} | Mean Δ24: +${m24:6.2f} | Mean Δ120: +${m120:7.2f} | Win Rate: {wr:5.1f}%")

    print("==================================================================================", flush=True)

if __name__ == "__main__":
    analyze_mcv_dataset()
