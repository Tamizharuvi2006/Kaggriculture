"""PHASE 89: ENDGAME REBOUND SURVIVABILITY LAB.

Objective: Evaluate whether reserving a small "Endgame Premium Inventory" buffer (4-8 units of Straw/Milk)
during endgame price crashes (Steps 576-719) improves final wealth when a late-game price rebound occurs,
or whether it penalizes final wealth on seeds where prices never rebound.

Controlled Arms (30 Harsh/Crashed Commodity Seeds | 4-Worker Multiprocessing):
- Arm 1: Control (APEX 3.5 Candidate Frozen Baseline)
- Arm 2: Endgame Premium Reservation (Holds 6u Straw / 6u Milk during crashes, liquidating on Step 715)

Outputs: reports/PHASE89_ENDGAME_REBOUND_SURVIVABILITY_REPORT.md
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

_WORKER_APEX35_AGENT = None
_WORKER_BASE_AGENT = None

def init_worker():
    global _WORKER_APEX35_AGENT, _WORKER_BASE_AGENT
    apex35_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex35.py")
    spec = importlib.util.spec_from_file_location("apex35_mod", apex35_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _WORKER_APEX35_AGENT = mod.agent

    base_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec_b = importlib.util.spec_from_file_location("base_mod", base_path)
    mod_b = importlib.util.module_from_spec(spec_b)
    spec_b.loader.exec_module(mod_b)
    _WORKER_BASE_AGENT = mod_b.agent

def make_reservation_agent():
    """Builds APEX 3.5 with Endgame Premium Inventory Reservation."""
    def agent(obs):
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        farms = obs.get("farms") or []
        p_idx = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        my_farm = farms[p_idx] if len(farms) > p_idx else {}
        my_money = float(my_farm.get("money", 0.0) or 0.0)
        unlocked = len(my_farm.get("unlocked_quadrants") or [])

        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        milk_in_shed = int(shed.get("MILK", 0) or 0)

        mkt = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt.get("prices") or {}
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)
        p_milk = float(prices.get("MILK", 193.0) or 193.0)

        base_act = _WORKER_APEX35_AGENT(obs)
        if not isinstance(base_act, dict):
            return base_act

        # Only apply reservation in endgame (step >= 576) when Land #3 is unlocked and cash is safe (> $800)
        if step >= 576 and step < 710 and unlocked >= 3 and my_money >= 800.0:
            market_orders = list(base_act.get("market") or [])
            filtered_orders = []

            for m in market_orders:
                if isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL":
                    item = m[1]
                    qty = int(m[2]) if len(m) > 2 else 1

                    # If Straw price is crashed (< $140) and we have low shed stock, hold 6u premium reserve
                    if item == "STRAWBERRY" and p_straw < 140.0:
                        sellable = max(0, straw_in_shed - 6)
                        if sellable > 0:
                            filtered_orders.append(["SELL", "STRAWBERRY", min(qty, sellable)])
                        continue

                    # If Milk price is crashed (< $120) and we have low shed stock, hold 6u premium reserve
                    if item == "MILK" and p_milk < 120.0:
                        sellable = max(0, milk_in_shed - 6)
                        if sellable > 0:
                            filtered_orders.append(["SELL", "MILK", min(qty, sellable)])
                        continue

                filtered_orders.append(m)

            base_act["market"] = filtered_orders

        return base_act

    return agent

def run_phase89_match(args: Tuple[str, str, int]) -> Dict[str, Any]:
    global _WORKER_APEX35_AGENT, _WORKER_BASE_AGENT
    arm_id, policy_type, seed = args

    if policy_type == "control":
        agent0 = _WORKER_APEX35_AGENT
    elif policy_type == "reservation":
        agent0 = make_reservation_agent()
    else:
        raise ValueError(f"Unknown policy_type: {policy_type}")

    agent1 = _WORKER_BASE_AGENT

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, agent1])
    obs = trainer.reset()

    for s in range(720):
        act = agent0(obs)
        obs, rew, done, info = trainer.step(act)
        if done: break

    w0 = float(rew or 0.0)
    farms = obs.get("farms") or []
    w1 = float(farms[1].get("money", 0.0) or 0.0) if len(farms) > 1 else 0.0

    total_pie = w0 + w1
    capture_share = (w0 / max(1.0, total_pie)) * 100.0

    return {
        "arm_id": arm_id,
        "policy_type": policy_type,
        "seed": seed,
        "wealth0": w0,
        "wealth1": w1,
        "total_pie": total_pie,
        "capture_share": capture_share,
        "win": 1 if w0 > w1 else 0,
        "loss": 1 if w0 < w1 else 0,
    }

def run_phase89_experiment():
    processes = 4
    print("====================================================================================================", flush=True)
    print(f"🔬 PHASE 89: ENDGAME REBOUND SURVIVABILITY LAB ({processes} WORKERS | 30 HARSH SEEDS)", flush=True)
    print("====================================================================================================", flush=True)

    # 30 Harsh / Crashed Commodity Seeds (including live seed 1205390807)
    harsh_seeds = [1205390807] + [125000 + i * 83 for i in range(29)]

    arms = [
        ("Arm 1: APEX 3.5 Control (Frozen Candidate Baseline)", "arm1_control", "control", harsh_seeds),
        ("Arm 2: Endgame Premium Reservation (Holds 6u Reserve on Crashes)", "arm2_reservation", "reservation", harsh_seeds),
    ]

    arm_results = {}

    with multiprocessing.Pool(processes=processes, initializer=init_worker) as pool:
        for arm_title, arm_id, policy_type, seed_list in arms:
            print(f"--- ⚔️ EVALUATING: {arm_title} ({len(seed_list)} Seeds) ---", flush=True)
            tasks = [(arm_id, policy_type, s) for s in seed_list]
            res = pool.map(run_phase89_match, tasks)

            w0_list = [r["wealth0"] for r in res]
            w1_list = [r["wealth1"] for r in res]
            pie_list = [r["total_pie"] for r in res]
            wins = sum(r["win"] for r in res)
            losses = sum(r["loss"] for r in res)

            avg_w0 = sum(w0_list) / len(w0_list)
            avg_w1 = sum(w1_list) / len(w1_list)
            avg_pie = sum(pie_list) / len(pie_list)
            win_rate = (wins / len(seed_list)) * 100.0

            print(f"  Our Wealth: ${avg_w0:,.2f} | Opponent Wealth: ${avg_w1:,.2f} | Total Pie: ${avg_pie:,.2f}")
            print(f"  Win Rate: {win_rate:.1f}% ({wins}W-{losses}L)\n", flush=True)

            arm_results[arm_id] = {
                "title": arm_title,
                "w0": avg_w0,
                "w1": avg_w1,
                "pie": avg_pie,
                "win_rate": win_rate,
                "wins": wins,
                "losses": losses,
            }

    control_w0 = arm_results["arm1_control"]["w0"]
    reserve_w0 = arm_results["arm2_reservation"]["w0"]
    delta = reserve_w0 - control_w0

    print("====================================================================================================", flush=True)
    print(f"📊 PHASE 89 EXPERIMENTAL RESULT: Net Delta = ${delta:+,.2f} per match")
    print("====================================================================================================", flush=True)

    report_md = f"""# 📜 Phase 89: Endgame Rebound Survivability Report

> **Research Purpose**: Evaluate whether reserving an **Endgame Premium Inventory Buffer (6u Straw / 6u Milk)** during price crashes (Steps 576–719) improves final wealth when late rebounds occur.
> **Core Result**: **Control Wealth = ${control_w0:,.2f}** vs **Reservation Wealth = ${reserve_w0:,.2f}** (**Net Delta = ${delta:+,.2f}**).

---

## 📊 1. Master Head-to-Head Comparison (30 Harsh Seeds)

| Counterfactual Arm | Our Mean Wealth ($) | Opponent Wealth ($) | Total Economic Pie ($) | Win Rate (%) | Net Delta ($) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 🛡️ **Arm 1: APEX 3.5 Control** | **${control_w0:,.2f}** | ${arm_results['arm1_control']['w1']:,.2f} | **${arm_results['arm1_control']['pie']:,.2f}** | **{arm_results['arm1_control']['win_rate']:.1f}%** | Baseline |
| 🧪 **Arm 2: Endgame Reservation** | **${reserve_w0:,.2f}** | ${arm_results['arm2_reservation']['w1']:,.2f} | **${arm_results['arm2_reservation']['pie']:,.2f}** | **{arm_results['arm2_reservation']['win_rate']:.1f}%** | **${delta:+,.2f}** |

---

## 💡 2. Strategic Synthesis & Policy Decision

1. **Empirical Valuation**:
   - If `delta <= 0`: Holding inventory during crashes on harsh seeds **penalizes net wealth** by forcing low-value liquidations at Step 715 when prices fail to rebound.
   - If `delta > 0`: Reserving premium inventory successfully captures late-game price spikes.

2. **Policy Governance**:
   - APEX 3.5 Candidate remains **100% FROZEN LOCALLY**. Zero code changes executed on live submission.
"""

    report_path = os.path.join(BASE_DIR, "reports", "PHASE89_ENDGAME_REBOUND_SURVIVABILITY_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Report written to: {report_path}", flush=True)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_phase89_experiment()
