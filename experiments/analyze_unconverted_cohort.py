"""Detailed Forensic Analysis of the 42 Unconverted Positive-Alpha Matches in EXP125."""
from __future__ import annotations
import os
import sys
import json
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

with open(os.path.join(REPORTS_DIR, "exp125_deficit_predictor_results.json"), "r", encoding="utf-8") as f:
    matches = json.load(f)

# Flatten checkpoint records
rows = []
for m in matches:
    cohort = m["cohort"]
    match_id = m["match_id"]
    seed = m["seed"]
    seat = m["seat"]
    d1_rew = m["telemetry"]["d1_final_reward"]
    opp_rew = m["telemetry"]["opp_final_reward"]
    final_deficit = opp_rew - d1_rew
    exp124_delta = m["exp124_delta"]

    for day in [5, 10, 15, 20, 25, 27, 29]:
        cp_key = f"day_{day}"
        if cp_key not in m["telemetry"]["checkpoints"]:
            continue
        cp = m["telemetry"]["checkpoints"][cp_key]
        d1_m = cp["d1_metrics"]
        opp_m = cp["opp_metrics"]

        rows.append({
            "match_id": match_id,
            "seed": seed,
            "seat": seat,
            "cohort": cohort,
            "day": day,
            "d1_rew": d1_rew,
            "opp_rew": opp_rew,
            "final_deficit": final_deficit,
            "exp124_delta": exp124_delta,
            "d1_money": d1_m["money"],
            "opp_money": opp_m["money"],
            "money_deficit": opp_m["money"] - d1_m["money"],
            "d1_wealth": d1_m["total_estimated_wealth"],
            "opp_wealth": opp_m["total_estimated_wealth"],
            "wealth_deficit": opp_m["total_estimated_wealth"] - d1_m["total_estimated_wealth"],
            "d1_cows": d1_m["cows"],
            "opp_cows": opp_m["cows"],
            "cow_lead": opp_m["cows"] - d1_m["cows"],
            "d1_sheep": d1_m["sheep"],
            "opp_sheep": opp_m["sheep"],
            "sheep_lead": opp_m["sheep"] - d1_m["sheep"],
            "d1_plants": d1_m["plants"],
            "opp_plants": opp_m["plants"],
            "d1_strawberries": d1_m["strawberries"],
            "opp_strawberries": opp_m["strawberries"],
            "d1_unharvested": d1_m["unharvested_yield"],
            "d1_ripe": d1_m["ripe_strawberries"],
            "milk_price": cp["milk_price"],
            "wool_price": cp["wool_price"],
            "straw_price": cp["straw_price"],
            "wheat_price": cp["wheat_price"],
        })

df = pd.DataFrame(rows)

print("=" * 135)
print("DEEP FORENSIC BREAKDOWN: 42 UNCONVERTED vs 6 CONVERTED vs 52 UNAFFECTED MATCHES")
print("=" * 135)

for day in [5, 10, 15, 20, 25]:
    sub = df[df["day"] == day]
    c = sub[sub["cohort"] == "CONVERTED"]
    u = sub[sub["cohort"] == "UNCONVERTED_POSITIVE"]
    a = sub[sub["cohort"] == "UNAFFECTED"]

    print(f"\n>>> CHECKPOINT: DAY {day:02d}")
    metrics = [
        ("wealth_deficit", "Opponent Wealth Lead ($)"),
        ("money_deficit", "Opponent Cash Lead ($)"),
        ("cow_lead", "Opponent Cow Lead"),
        ("sheep_lead", "Opponent Sheep Lead"),
        ("opp_strawberries", "Opponent Strawberry Plots"),
        ("d1_strawberries", "D.1 Strawberry Plots"),
        ("d1_unharvested", "D.1 Trapped Ripe Yield"),
        ("milk_price", "Market Milk Price ($)"),
        ("wool_price", "Market Wool Price ($)"),
        ("straw_price", "Market Strawberry Price ($)"),
    ]

    print(f"{'Feature':<30} | {'CONVERTED (6)':<18} | {'UNCONVERTED (42)':<18} | {'UNAFFECTED (52)':<18} | {'U vs C p-val':<12} | {'U vs A p-val'}")
    print("-" * 125)
    for col, label in metrics:
        c_m, u_m, a_m = c[col].mean(), u[col].mean(), a[col].mean()
        # Welch's t-test
        p_uc = stats.ttest_ind(u[col], c[col], equal_var=False).pvalue if len(c[col]) > 1 else 1.0
        p_ua = stats.ttest_ind(u[col], a[col], equal_var=False).pvalue if len(a[col]) > 1 else 1.0

        p_uc_str = f"{p_uc:.4f}" if p_uc < 0.05 else f"{p_uc:.2f} (ns)"
        p_ua_str = f"{p_ua:.4f}" if p_ua < 0.05 else f"{p_ua:.2f} (ns)"

        print(f"{label:<30} | {c_m:12,.1f}     | {u_m:12,.1f}     | {a_m:12,.1f}     | {p_uc_str:<12} | {p_ua_str}")

# Correlation of Day 10/15 features with the remaining terminal deficit in the 42 unconverted matches
print("\n" + "=" * 135)
print("FEATURE CORRELATION WITH REMAINING DEFICIT (FOR THE 42 UNCONVERTED MATCHES)")
print("=" * 135)
sub42_d10 = df[(df["day"] == 10) & (df["cohort"] == "UNCONVERTED_POSITIVE")]
sub42_d15 = df[(df["day"] == 15) & (df["cohort"] == "UNCONVERTED_POSITIVE")]

for d_num, d_sub in [(10, sub42_d10), (15, sub42_d15)]:
    print(f"\nDay {d_num} Correlations with Final Deficit:")
    for feat in ["wealth_deficit", "money_deficit", "sheep_lead", "cow_lead", "milk_price", "wool_price", "straw_price", "d1_unharvested"]:
        r, p = stats.pearsonr(d_sub[feat], d_sub["final_deficit"])
        print(f"  - {feat:<20}: r = {r:+.3f} (p = {p:.4f})")
