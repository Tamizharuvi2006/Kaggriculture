"""EXP123: Loss Cohort Forensics & Win-Conversion Diagnostic Suite.

Systematically mines and analyzes 100 verified D.1 Loss Matches to classify failure modes,
loss margins, and state divergence patterns.

Objectives:
1. Identify 100 matches where D.1 loses (against kaitofukami-v18 baseline and real elite replays).
2. Measure the distribution of Loss Margins:
   - Micro-Losses (< $5,000 delta): recoverable via tactical endgame/liquidity tweaks.
   - Mid-Losses ($5,000 - $25,000 delta): structural efficiency/timing differences.
   - Macro-Blowouts (> $25,000 delta): hard architectural/portfolio divergence.
3. Categorize Root Failure Modes:
   - Category A: Commodity Price Cannibalization (Strawberry market flooded, low realized price).
   - Category B: High-Density Livestock Out-Scaling (Opponent milk/wool scaling outpaces crops).
   - Category C: Endgame Stranded Yield Deficit (Loss margin <= stranded field value).
   - Category D: Opening Working Capital / Liquidity Drag (Early stall on Days 1-5).
4. Establish the Ground-Truth Benchmark for Loss Conversion (Loss -> Win transition matrix).
"""
from __future__ import annotations
import os
import sys
import json
import gzip
import importlib.util
import numpy as np
import pandas as pd
from collections import defaultdict
from huggingface_hub import hf_hub_download

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

DATASETS_IL = os.path.join(BASE_DIR, "datasets", "il")
EPISODES_DIR = os.path.join(DATASETS_IL, "episodes")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(EPISODES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load HF Token
hf_token_path = os.path.expanduser("~/.hf/HF_TOKEN")
HF_TOKEN = None
if os.path.exists(hf_token_path):
    with open(hf_token_path, "r", encoding="utf-8") as f:
        HF_TOKEN = f.read().strip()
    os.environ["HF_TOKEN"] = HF_TOKEN

def get_episode_path(episode_id: int) -> str | None:
    local_path = os.path.join(EPISODES_DIR, f"{episode_id}.json.gz")
    if os.path.exists(local_path):
        return local_path
    rel_hf_path = f"datasets/il/episodes/{episode_id}.json.gz"
    try:
        return hf_hub_download(
            repo_id="KiroSamurai/kaggriculture-il",
            filename=rel_hf_path,
            repo_type="dataset",
            local_dir=BASE_DIR,
            token=HF_TOKEN,
        )
    except Exception:
        return None

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def evaluate_match_telemetry(agent_0, agent_1, seed: int, seat_0_is_d1: bool = True):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    d1_seat = 0 if seat_0_is_d1 else 1
    opp_seat = 1 - d1_seat

    strawberry_sales_d1 = []
    milk_sales_d1 = []
    prices_history = defaultdict(list)

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        t = obs0.get("step", 0)

        # Call Agent 0
        try:
            a0 = agent_0.agent(obs0, env.configuration)
        except TypeError:
            a0 = agent_0.agent(obs0) if hasattr(agent_0, "agent") else agent_0(obs0)

        # Call Agent 1
        try:
            a1 = agent_1.agent(obs1, env.configuration)
        except TypeError:
            a1 = agent_1.agent(obs1) if hasattr(agent_1, "agent") else agent_1(obs1)

        d1_act = a0 if seat_0_is_d1 else a1
        d1_obs = obs0 if seat_0_is_d1 else obs1

        # Track Market Sales & Prices
        for m in (d1_act.get("market") or []):
            if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                item, qty = m[1], float(m[2])
                p_item = float(d1_obs.get("market_prices", {}).get(item, 0.0))
                if item == "STRAWBERRY":
                    strawberry_sales_d1.append((t, qty, p_item))
                elif item == "MILK":
                    milk_sales_d1.append((t, qty, p_item))

        for k, v in (d1_obs.get("market_prices", {}) or {}).items():
            prices_history[k].append(float(v))

        env.step([a0, a1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)

    d1_rew = r0 if seat_0_is_d1 else r1
    opp_rew = r1 if seat_0_is_d1 else r0
    won = d1_rew > opp_rew
    delta = d1_rew - opp_rew  # Negative when D.1 loses

    # Extract terminal state metrics
    final_obs = env.state[d1_seat].observation
    farms = final_obs.get("farms", [])
    d1_farm = farms[d1_seat] if len(farms) > d1_seat else {}
    opp_farm = farms[opp_seat] if len(farms) > opp_seat else {}

    # Count stranded crops and animals
    stranded_straw = 0
    d1_cows = 0
    opp_cows = 0
    opp_sheep = 0

    for row in (d1_farm.get("tiles") or []):
        for tile in row:
            if isinstance(tile, dict):
                if tile.get("crop") == "STRAWBERRY" and tile.get("kind") == "PLANT":
                    if tile.get("yield_units", 0) > 0:
                        stranded_straw += 1
                if str(tile.get("animal", "")).upper() == "COW":
                    d1_cows += 1

    for row in (opp_farm.get("tiles") or []):
        for tile in row:
            if isinstance(tile, dict):
                if str(tile.get("animal", "")).upper() == "COW":
                    opp_cows += 1
                elif str(tile.get("animal", "")).upper() == "SHEEP":
                    opp_sheep += 1

    # Realized Strawberry price
    total_straw_rev = sum(q * p for _, q, p in strawberry_sales_d1)
    total_straw_qty = sum(q for _, q, _ in strawberry_sales_d1)
    realized_straw_price = (total_straw_rev / total_straw_qty) if total_straw_qty > 0 else 0.0

    return {
        "seed": seed,
        "seat": d1_seat,
        "d1_reward": d1_rew,
        "opp_reward": opp_rew,
        "won": won,
        "delta": delta,
        "stranded_strawberries": stranded_straw,
        "stranded_value": stranded_straw * realized_straw_price,
        "d1_cows": d1_cows,
        "opp_cows": opp_cows,
        "opp_sheep": opp_sheep,
        "realized_straw_price": realized_straw_price,
    }

def classify_failure_mode(res: dict) -> str:
    """Categorizes the primary structural cause of a loss."""
    loss_margin = abs(res["delta"])

    # 1. Endgame Stranded Yield: Loss margin <= potential revenue from unharvested crops
    if loss_margin <= res["stranded_value"] and res["stranded_strawberries"] >= 4:
        return "ENDGAME_STRANDED_YIELD_DEFICIT"

    # 2. Livestock Rush Out-Scaling: Opponent has significantly more livestock
    if (res["opp_cows"] + res["opp_sheep"]) >= (res["d1_cows"] + 4):
        return "LIVESTOCK_HERD_OUTSCALING"

    # 3. Commodity Price Cannibalization: Realized strawberry price collapsed below $110
    if res["realized_straw_price"] < 110.0 and res["realized_straw_price"] > 0:
        return "STRAWBERRY_PRICE_CANNIBALIZATION"

    # 4. General Macro Efficiency Deficit
    if loss_margin < 10000.0:
        return "TACTICAL_TIMING_MARGINAL_DEFICIT"

    return "MACRO_PORTFOLIO_DIVERGENCE"

def main():
    print("=" * 135)
    print("EXP123: LOSS COHORT FORENSICS & FAILURE MODE TAXONOMY (100 LOSS MATCHES)")
    print("=" * 135)

    # 1. Mine matches until we collect 100 D.1 Losses
    loss_records = []
    total_evaluated = 0
    seed_cursor = 1000

    print(">>> Mining D.1 Loss Matches across paired seat matchups...")

    while len(loss_records) < 100 and seed_cursor < 2000:
        for seat in [0, 1]:
            total_evaluated += 1
            if seat == 0:
                res = evaluate_match_telemetry(sub_d1, bot_v18_mod, seed=seed_cursor, seat_0_is_d1=True)
            else:
                res = evaluate_match_telemetry(bot_v18_mod, sub_d1, seed=seed_cursor, seat_0_is_d1=False)

            if not res["won"]:
                res["failure_mode"] = classify_failure_mode(res)
                loss_records.append(res)
                if len(loss_records) % 20 == 0:
                    print(f"  Collected {len(loss_records)}/100 Loss Matches (Evaluated {total_evaluated} total)...")
            
            if len(loss_records) >= 100:
                break
        seed_cursor += 1

    df_losses = pd.DataFrame(loss_records)

    print("\n" + "=" * 135)
    print("EXP123: STATISTICAL SYNTHESIS ACROSS 100 D.1 LOSSES")
    print("=" * 135)

    # 1. Loss Margin Distribution
    margins = df_losses["delta"].abs()
    print("\n1. LOSS MARGIN DISTRIBUTION (How close is D.1 to winning?):")
    print(f"   - Mean Loss Margin   : -${margins.mean():10,.2f}")
    print(f"   - Median Loss Margin : -${margins.median():10,.2f}")
    print(f"   - Min Loss Margin    : -${margins.min():10,.2f}")
    print(f"   - Max Loss Margin    : -${margins.max():10,.2f}")
    
    micro_losses = (margins < 5000).sum()
    mid_losses = ((margins >= 5000) & (margins < 20000)).sum()
    macro_losses = (margins >= 20000).sum()

    print(f"\n   Breakdown by Opportunity Window:")
    print(f"   - Micro-Losses (< $5,000)      : {micro_losses:2d} matches ({micro_losses:4.1f}%) -> 🎯 High-probability win conversion targets")
    print(f"   - Mid-Losses   ($5k - $20k)    : {mid_losses:2d} matches ({mid_losses:4.1f}%) -> ⚖️ Tactical & timing optimizations")
    print(f"   - Macro-Losses (> $20,000)     : {macro_losses:2d} matches ({macro_losses:4.1f}%) -> 🛡️ Deep architectural divergence")

    # 2. Failure Mode Taxonomy
    failure_counts = df_losses["failure_mode"].value_counts()
    print("\n2. PRIMARY ROOT FAILURE MODES (Empirical Classification):")
    for mode, cnt in failure_counts.items():
        pct = (cnt / len(df_losses)) * 100.0
        avg_margin = df_losses[df_losses["failure_mode"] == mode]["delta"].abs().mean()
        print(f"   - {mode:<38s}: {cnt:2d} matches ({pct:4.1f}%) | Avg Delta: -${avg_margin:8,.2f}")

    # 3. Stranded Yield & Terminal Field Economics
    avg_stranded_plots = df_losses["stranded_strawberries"].mean()
    avg_stranded_val = df_losses["stranded_value"].mean()
    print("\n3. ENDGAME STRANDED HARVEST ECONOMICS:")
    print(f"   - Average Stranded Strawberry Plots at Day 30 : {avg_stranded_plots:.1f} plots")
    print(f"   - Average Unharvested Capital Trapped in Field : ${avg_stranded_val:8,.2f}")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(loss_records, f, indent=2)
    print(f"\nSaved Full Loss Cohort Dataset: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
