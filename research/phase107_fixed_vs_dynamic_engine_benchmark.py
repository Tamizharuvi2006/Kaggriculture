"""PHASE 107: FIXED vs DYNAMIC CORE ENGINE BENCHMARK.

Objective: Prove whether submission.py (V4.1, rated 1479.8) uses a fundamentally
different engine path than APEX 3.6, and measure the performance difference.

Design:
- ARM A ("FIXED"): APEX 3.6 as-is (use_fixed_schedule=True, v18 replay route + APEX overlay)
- ARM B ("DYNAMIC"): submission.py as-is (use_fixed_schedule=False, dynamic engine + V8.4 overlay)
- OPPONENT: baseline/kaitofukami-v18.py (identical for both arms)
- SEEDS: identical for both arms

Cohorts:
1. Fresh Unseen Seat 0 (50 seeds: 20000-20049)
2. Fresh Unseen Seat 1 (50 seeds: 20000-20049)
3. Historical 11 Parity Losses (Seat 1)
4. 20 Champion Replay Seeds (Mixed Seat)
5. 100-Match Mixed Field (50 seeds × 2 seats: 20050-20099)

Measured metrics per arm:
- Win rate
- Mean wealth
- Mean opponent wealth
- Land #2 timing
- Land #3 timing

Output: reports/PHASE107_FIXED_VS_DYNAMIC_ENGINE_REPORT.md
"""

from __future__ import annotations
import sys
import os
import multiprocessing
import importlib.util
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

# Worker globals
_WORKER_FIXED_AGENT = None  # APEX 3.6 (use_fixed_schedule=True)
_WORKER_DYNAMIC_AGENT = None  # submission.py (use_fixed_schedule=False)
_WORKER_BASE_AGENT = None  # opponent


def init_worker():
    global _WORKER_FIXED_AGENT, _WORKER_DYNAMIC_AGENT, _WORKER_BASE_AGENT

    # ARM A: APEX 3.6 (Fixed engine)
    fixed_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex36.py")
    spec_f = importlib.util.spec_from_file_location("fixed_mod", fixed_path)
    mod_f = importlib.util.module_from_spec(spec_f)
    spec_f.loader.exec_module(mod_f)
    _WORKER_FIXED_AGENT = mod_f.agent

    # ARM B: submission.py (Dynamic engine)
    dynamic_path = os.path.join(BASE_DIR, "submission.py")
    spec_d = importlib.util.spec_from_file_location("dynamic_mod", dynamic_path)
    mod_d = importlib.util.module_from_spec(spec_d)
    spec_d.loader.exec_module(mod_d)
    _WORKER_DYNAMIC_AGENT = mod_d.agent

    # Opponent: baseline
    base_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec_b = importlib.util.spec_from_file_location("base_mod", base_path)
    mod_b = importlib.util.module_from_spec(spec_b)
    spec_b.loader.exec_module(mod_b)
    _WORKER_BASE_AGENT = mod_b.agent


def eval_match_task(args: Tuple[str, str, int, int]) -> Dict[str, Any]:
    global _WORKER_FIXED_AGENT, _WORKER_DYNAMIC_AGENT, _WORKER_BASE_AGENT
    cohort_name, arm, seed, seat = args

    agent_fn = _WORKER_FIXED_AGENT if arm == "FIXED" else _WORKER_DYNAMIC_AGENT

    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed}
    )
    if seat == 0:
        trainer = env.train([None, _WORKER_BASE_AGENT])
    else:
        trainer = env.train([_WORKER_BASE_AGENT, None])

    obs = trainer.reset()
    s_land2, s_land3 = None, None
    total_straw_sold, total_milk_sold = 0, 0
    total_sell_orders, total_pass_actions = 0, 0

    for s in range(720):
        farm_idx = seat
        farms = obs.get("farms") or []
        if len(farms) > farm_idx:
            quads = len(farms[farm_idx].get("unlocked_quadrants") or [])
            if quads >= 2 and s_land2 is None: s_land2 = s
            if quads >= 3 and s_land3 is None: s_land3 = s

        act = agent_fn(obs)

        # Track market activity
        market = act.get("market") or []
        for order in market:
            if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "SELL":
                total_sell_orders += 1
                if len(order) >= 3:
                    if order[1] == "STRAWBERRY":
                        total_straw_sold += int(order[2])
                    elif order[1] == "MILK":
                        total_milk_sold += int(order[2])

        # Track PASS actions
        farmer_act = act.get("farmer") or ["PASS"]
        if farmer_act == ["PASS"] or farmer_act == "PASS":
            total_pass_actions += 1
        for hand_act in (act.get("hands") or []):
            if hand_act == ["PASS"] or hand_act == "PASS":
                total_pass_actions += 1

        obs, rew, done, info = trainer.step(act)
        if done:
            break

    my_wealth = float(rew or 0.0)
    opp_idx = 1 - seat
    opp_wealth = float(obs["farms"][opp_idx].get("money", 0.0) or 0.0)
    win = 1 if my_wealth > opp_wealth else 0

    return {
        "cohort": cohort_name,
        "arm": arm,
        "seed": seed,
        "seat": seat,
        "wealth": my_wealth,
        "opp_wealth": opp_wealth,
        "win": win,
        "s_land2": s_land2 or 170,
        "s_land3": s_land3 or 261,
        "straw_sold": total_straw_sold,
        "milk_sold": total_milk_sold,
        "sell_orders": total_sell_orders,
        "pass_actions": total_pass_actions,
    }


def run_phase107():
    processes = 8
    print("=" * 100)
    print(f"🔬 PHASE 107: FIXED vs DYNAMIC CORE ENGINE BENCHMARK ({processes} WORKERS)")
    print("=" * 100 + "\n")

    # Cohort definitions
    parity_seeds = [
        92821576, 92820867, 92744887, 92665598, 92670343,
        92677877, 92680700, 92662754, 92684467, 92792740, 92678835
    ]
    champ_seeds = [
        90561400, 90565860, 90576395, 90620861, 90637254,
        90656094, 90666014, 90676450, 90687053, 90703831,
        90715367, 90729793, 90737497, 90747447, 90757279,
        90767228, 90777505, 90788647, 90812739, 90827253
    ]
    fresh_seeds = list(range(20000, 20050))
    mixed_seeds = list(range(20050, 20100))

    tasks = []

    # Cohort 1: Seat 0 Fresh (50 seeds × 2 arms = 100 episodes)
    for seed in fresh_seeds:
        tasks.append(("Seat 0 Fresh", "FIXED", seed, 0))
        tasks.append(("Seat 0 Fresh", "DYNAMIC", seed, 0))

    # Cohort 2: Seat 1 Fresh (50 seeds × 2 arms = 100 episodes)
    for seed in fresh_seeds:
        tasks.append(("Seat 1 Fresh", "FIXED", seed, 1))
        tasks.append(("Seat 1 Fresh", "DYNAMIC", seed, 1))

    # Cohort 3: Historical Parity (11 seeds × 2 arms, Seat 1)
    for seed in parity_seeds:
        tasks.append(("Parity Losses", "FIXED", seed, 1))
        tasks.append(("Parity Losses", "DYNAMIC", seed, 1))

    # Cohort 4: Champion Seeds (20 seeds × 2 arms, Seat 0)
    for seed in champ_seeds:
        tasks.append(("Champion Seeds", "FIXED", seed, 0))
        tasks.append(("Champion Seeds", "DYNAMIC", seed, 0))

    # Cohort 5: Mixed Field (50 seeds × 2 seats × 2 arms = 200 episodes)
    for seed in mixed_seeds:
        for seat in [0, 1]:
            tasks.append(("Mixed Field", "FIXED", seed, seat))
            tasks.append(("Mixed Field", "DYNAMIC", seed, seat))

    total_episodes = len(tasks)
    print(f"📊 Total episodes to evaluate: {total_episodes}")
    print(f"   Cohort 1 (Seat 0 Fresh): 100 episodes (50 per arm)")
    print(f"   Cohort 2 (Seat 1 Fresh): 100 episodes (50 per arm)")
    print(f"   Cohort 3 (Parity Losses): 22 episodes (11 per arm)")
    print(f"   Cohort 4 (Champion Seeds): 40 episodes (20 per arm)")
    print(f"   Cohort 5 (Mixed Field): 200 episodes (100 per arm)")
    print(f"\n🚀 Launching {processes}-worker parallel evaluation...\n")

    with multiprocessing.Pool(processes=processes, initializer=init_worker) as pool:
        results = pool.map(eval_match_task, tasks)

    print(f"\n✅ All {total_episodes} episodes complete.\n")

    # Aggregate results by cohort and arm
    cohorts = {}
    for r in results:
        key = (r["cohort"], r["arm"])
        if key not in cohorts:
            cohorts[key] = []
        cohorts[key].append(r)

    # Build report
    report_lines = [
        "# 📜 Phase 107: Fixed vs Dynamic Core Engine Benchmark Report\n",
        "> **Objective**: Determine whether `submission.py` (V4.1, rated 1479.8) uses a fundamentally",
        "> different engine path than APEX 3.6, and measure the performance difference.\n",
        f"> **Total Episodes**: {total_episodes} full 720-step episodes across 5 cohorts, 2 arms each.",
        f"> **Multiprocessing**: {processes} worker processes.\n",
        "---\n",
        "## 📊 1. Master Comparison Table\n",
        "| Cohort | Arm | Episodes | Win Rate | Mean Wealth | Mean Opp Wealth | Margin | L2 Step | L3 Step | Straw Sold | Milk Sold | Sell Orders | PASS Actions |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    cohort_names_ordered = ["Seat 0 Fresh", "Seat 1 Fresh", "Parity Losses", "Champion Seeds", "Mixed Field"]
    for cohort_name in cohort_names_ordered:
        for arm in ["FIXED", "DYNAMIC"]:
            key = (cohort_name, arm)
            if key not in cohorts:
                continue
            data = cohorts[key]
            n = len(data)
            wins = sum(r["win"] for r in data)
            wr = wins / n * 100 if n > 0 else 0
            mean_w = sum(r["wealth"] for r in data) / n if n > 0 else 0
            mean_opp = sum(r["opp_wealth"] for r in data) / n if n > 0 else 0
            margin = mean_w - mean_opp
            mean_l2 = sum(r["s_land2"] for r in data) / n if n > 0 else 0
            mean_l3 = sum(r["s_land3"] for r in data) / n if n > 0 else 0
            mean_straw = sum(r["straw_sold"] for r in data) / n if n > 0 else 0
            mean_milk = sum(r["milk_sold"] for r in data) / n if n > 0 else 0
            mean_sells = sum(r["sell_orders"] for r in data) / n if n > 0 else 0
            mean_pass = sum(r["pass_actions"] for r in data) / n if n > 0 else 0
            report_lines.append(
                f"| **{cohort_name}** | **{arm}** | {n} | **{wr:.1f}%** ({wins}/{n}) | "
                f"${mean_w:,.2f} | ${mean_opp:,.2f} | ${margin:+,.2f} | "
                f"{mean_l2:.1f} | {mean_l3:.1f} | {mean_straw:.1f} | {mean_milk:.1f} | "
                f"{mean_sells:.1f} | {mean_pass:.1f} |"
            )

    report_lines.append("\n---\n")

    # Per-cohort deltas
    report_lines.append("## 📊 2. Per-Cohort DYNAMIC vs FIXED Delta Summary\n")
    report_lines.append("| Cohort | FIXED WR | DYNAMIC WR | WR Delta | FIXED Wealth | DYNAMIC Wealth | Wealth Delta |")
    report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for cohort_name in cohort_names_ordered:
        f_key = (cohort_name, "FIXED")
        d_key = (cohort_name, "DYNAMIC")
        if f_key not in cohorts or d_key not in cohorts:
            continue
        f_data = cohorts[f_key]
        d_data = cohorts[d_key]
        f_wr = sum(r["win"] for r in f_data) / len(f_data) * 100
        d_wr = sum(r["win"] for r in d_data) / len(d_data) * 100
        f_w = sum(r["wealth"] for r in f_data) / len(f_data)
        d_w = sum(r["wealth"] for r in d_data) / len(d_data)
        report_lines.append(
            f"| **{cohort_name}** | {f_wr:.1f}% | {d_wr:.1f}% | **{d_wr - f_wr:+.1f}%** | "
            f"${f_w:,.2f} | ${d_w:,.2f} | **${d_w - f_w:+,.2f}** |"
        )

    report_lines.append("\n---\n")

    # Seed-level match comparison for Cohort 5 (Mixed Field)
    report_lines.append("## 📊 3. Head-to-Head Seed Comparison (Mixed Field)\n")
    report_lines.append("Counting seeds where DYNAMIC wins vs FIXED wins vs ties:\n")

    f_mixed = {r["seed"]: r for r in cohorts.get(("Mixed Field", "FIXED"), []) if r["seat"] == 0}
    d_mixed = {r["seed"]: r for r in cohorts.get(("Mixed Field", "DYNAMIC"), []) if r["seat"] == 0}
    dyn_better = 0
    fix_better = 0
    ties = 0
    for seed in f_mixed:
        if seed in d_mixed:
            if d_mixed[seed]["wealth"] > f_mixed[seed]["wealth"]:
                dyn_better += 1
            elif f_mixed[seed]["wealth"] > d_mixed[seed]["wealth"]:
                fix_better += 1
            else:
                ties += 1

    report_lines.append(f"- **DYNAMIC wins more wealth**: {dyn_better} seeds")
    report_lines.append(f"- **FIXED wins more wealth**: {fix_better} seeds")
    report_lines.append(f"- **Tied**: {ties} seeds\n")

    report_lines.append("---\n")
    report_lines.append("## 🏛️ Governance\n")
    report_lines.append("- 🛡️ **No code was modified**. This is a pure read-only benchmark.")
    report_lines.append("- 🛡️ **APEX 3.5 (`Ref 55483322`) remains active on Kaggle**.")
    report_lines.append("- 🛡️ **No submission, no git push.**")

    report_path = os.path.join(BASE_DIR, "reports", "PHASE107_FIXED_VS_DYNAMIC_ENGINE_REPORT.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # Print summary table
    print("\n" + "=" * 100)
    print("📊 PHASE 107: FIXED vs DYNAMIC CORE ENGINE BENCHMARK RESULTS")
    print("=" * 100)
    print(f"{'Cohort':<25} | {'Arm':<10} | {'WR':>10} | {'Mean Wealth':>14} | {'Straw':>8} | {'Milk':>8} | {'Sells':>6} | {'PASS':>6}")
    print("-" * 100)

    for cohort_name in cohort_names_ordered:
        for arm in ["FIXED", "DYNAMIC"]:
            key = (cohort_name, arm)
            if key not in cohorts:
                continue
            data = cohorts[key]
            n = len(data)
            wins = sum(r["win"] for r in data)
            wr = wins / n * 100 if n > 0 else 0
            mean_w = sum(r["wealth"] for r in data) / n if n > 0 else 0
            mean_straw = sum(r["straw_sold"] for r in data) / n if n > 0 else 0
            mean_milk = sum(r["milk_sold"] for r in data) / n if n > 0 else 0
            mean_sells = sum(r["sell_orders"] for r in data) / n if n > 0 else 0
            mean_pass = sum(r["pass_actions"] for r in data) / n if n > 0 else 0
            print(f"{cohort_name:<25} | {arm:<10} | {wr:>8.1f}% | ${mean_w:>12,.2f} | {mean_straw:>8.1f} | {mean_milk:>8.1f} | {mean_sells:>6.1f} | {mean_pass:>6.1f}")
        print("-" * 100)

    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    run_phase107()
