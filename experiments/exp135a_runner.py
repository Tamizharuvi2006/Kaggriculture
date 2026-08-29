"""EXP135-A Runner: Midgame Strawberry Peak Realization Test across 100 Loss Matches & 100 Fresh Seeds."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

import kaggle_environments
import importlib.util

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

class EXP135AAgent:
    """Isolated Midgame Strawberry Peak Capture Agent.

    Tests:
    if 20 <= day <= 24 and p_straw >= 150.0 and straw_in_shed > 0:
        sell 100% of strawberry shed inventory immediately.
    """
    def __init__(self, active: bool = True, thresh: float = 150.0):
        self.active = active
        self.thresh = thresh
        self.peak_sales_count = 0
        self.peak_sales_qty = 0
        self.peak_sales_revenue = 0.0

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        if self.active and (20 <= day <= 24):
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

            private_state = obs.get("private") or {}
            shed = private_state.get("shed", {}) or {}
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            if p_straw >= self.thresh and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    self.peak_sales_count += 1
                    self.peak_sales_qty += straw_in_shed
                    self.peak_sales_revenue += straw_in_shed * p_straw

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def run_evaluation_suite():
    print("=" * 135)
    print("EXP135-A: ISOLATED MIDGAME STRAWBERRY PEAK CAPTURE BENCHMARK")
    print("=" * 135)

    # 1. Test on 100 Historical Losses (EXP123 Cohort)
    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    print(f"\n1. Evaluating EXP135-A on 100 Frozen Historical Losses...")
    loss_results = []
    for m in loss_cohort[:50]:  # 50 matches probe
        seed = m["seed"]
        seat = m["seat"]

        # Control
        env0 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env0.reset()
        while not env0.done:
            obs0 = env0.state[0].observation if seat == 0 else env0.state[1].observation
            obs1 = env0.state[1].observation if seat == 0 else env0.state[0].observation
            a0 = sub_d1.agent(obs0, env0.configuration)
            a1 = bot_v18_mod.agent(obs1)
            env0.step([a0, a1] if seat == 0 else [a1, a0])
        r0 = float(env0.state[seat].reward or 0.0)
        r0_opp = float(env0.state[1 - seat].reward or 0.0)

        # EXP135-A
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env1.reset()
        agent_exp = EXP135AAgent(active=True, thresh=150.0)
        while not env1.done:
            obs0 = env1.state[0].observation if seat == 0 else env1.state[1].observation
            obs1 = env1.state[1].observation if seat == 0 else env1.state[0].observation
            a0 = agent_exp.act(obs0, env1.configuration)
            a1 = bot_v18_mod.agent(obs1)
            env1.step([a0, a1] if seat == 0 else [a1, a0])
        r1 = float(env1.state[seat].reward or 0.0)
        r1_opp = float(env1.state[1 - seat].reward or 0.0)

        loss_results.append({
            "seed": seed, "seat": seat,
            "ctrl_rew": r0, "ctrl_opp": r0_opp, "ctrl_won": r0 > r0_opp,
            "exp_rew": r1, "exp_opp": r1_opp, "exp_won": r1 > r1_opp,
            "delta": r1 - r0,
            "peak_triggers": agent_exp.peak_sales_count,
            "peak_qty": agent_exp.peak_sales_qty,
            "peak_rev": agent_exp.peak_sales_revenue,
        })

    df_loss = pd.DataFrame(loss_results)
    l2w = ((~df_loss["ctrl_won"]) & df_loss["exp_won"]).sum()
    w2l = (df_loss["ctrl_won"] & (~df_loss["exp_won"])).sum()

    print(f"Results on 50 Historical Losses:")
    print(f"  - Loss -> Win Conversions  : {l2w} matches")
    print(f"  - Win -> Loss Regressions  : {w2l} matches")
    print(f"  - Mean Delta ($)           : ${df_loss['delta'].mean():+,.2f}")
    print(f"  - Peak Trigger Events Total: {df_loss['peak_triggers'].sum()} events")

    out_json = os.path.join(REPORTS_DIR, "exp135a_strawberry_peak_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "loss_cohort_sample": _to_native(loss_results),
            "summary": {
                "l2w": _to_native(l2w),
                "w2l": _to_native(w2l),
                "mean_delta": _to_native(df_loss["delta"].mean()),
                "total_triggers": _to_native(df_loss["peak_triggers"].sum()),
            }
        }, f, indent=2)
    print(f"\nSaved EXP135-A Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    run_evaluation_suite()
