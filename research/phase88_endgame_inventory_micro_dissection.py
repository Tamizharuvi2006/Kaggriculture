"""PHASE 88 MICRO-DISSECTION: ENDGAME INVENTORY & PRICE TRAJECTORY FOR SEED 1205390807.

Extracts exact Step 576..719 telemetry:
- Our Straw & Milk shed inventory
- Market Strawberry & Milk prices
- Exact sale quantities & cash realized
"""

from __future__ import annotations
import sys
import os
import json
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

apex35_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex35.py")
spec = importlib.util.spec_from_file_location("apex35_mod", apex35_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_apex35 = mod.agent

base_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
spec_b = importlib.util.spec_from_file_location("base_mod", base_path)
mod_b = importlib.util.module_from_spec(spec_b)
spec_b.loader.exec_module(mod_b)
agent_opp = mod_b.agent

def micro_dissect_endgame():
    seed = 1205390807
    print(f"🔬 EXTRACTING EXACT ENDGAME INVENTORY TELEMETRY (STEPS 576-719) FOR SEED {seed}...", flush=True)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, agent_opp])
    obs = trainer.reset()

    records = []

    for step in range(720):
        farms = obs.get("farms") or []
        f0 = farms[0] if len(farms) > 0 else {}
        f1 = farms[1] if len(farms) > 1 else {}

        w0 = float(f0.get("money", 0.0) or 0.0)
        w1 = float(f1.get("money", 0.0) or 0.0)

        priv0 = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed0 = priv0.get("shed") or {}
        s_shed0 = int(shed0.get("STRAWBERRY", 0) or 0)
        m_shed0 = int(shed0.get("MILK", 0) or 0)

        mkt = obs.get("market") or {}
        prices = mkt.get("prices") or {}
        p_s = float(prices.get("STRAWBERRY", 0.0) or 0.0)
        p_m = float(prices.get("MILK", 0.0) or 0.0)

        act0 = agent_apex35(obs)
        our_sells = []
        for m in (act0.get("market") or []):
            if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL":
                our_sells.append(m)

        obs, rew, done, info = trainer.step(act0)

        w0_post = float(rew or 0.0)
        w1_post = float(farms[1].get("money", 0.0) or 0.0) if len(farms) > 1 else 0.0

        if step >= 576 and step % 12 == 0 or step in (671, 672, 715, 718, 719):
            records.append({
                "step": step,
                "our_cash": w0_post,
                "opp_cash": w1_post,
                "delta": w0_post - w1_post,
                "straw_price": p_s,
                "milk_price": p_m,
                "straw_shed": s_shed0,
                "milk_shed": m_shed0,
                "sells": our_sells,
            })

        if done: break

    print("\n====================================================================================================", flush=True)
    print("📊 ENDGAME STEP-BY-STEP INVENTORY & PRICE DISSECTION", flush=True)
    print("====================================================================================================", flush=True)
    print("Step | Our Cash     | Opp Cash     | Delta      | Straw Price | Milk Price | Shed Straw | Shed Milk | Sells Executed")
    print("-" * 115)
    for r in records:
        sells_str = str(r["sells"]) if r["sells"] else "-"
        print(f"{r['step']:<5}| ${r['our_cash']:>11,.2f} | ${r['opp_cash']:>11,.2f} | ${r['delta']:>10,.2f} | ${r['straw_price']:>11.2f} | ${r['milk_price']:>10.2f} | {r['straw_shed']:>10} | {r['milk_shed']:>9} | {sells_str}")
    print("====================================================================================================\n", flush=True)

if __name__ == "__main__":
    micro_dissect_endgame()
