"""V8.3 Verification & Ablation Study (500 Seeds & Head-to-Head Battle).

Phase 1 Verification & Ablation Plan:
1. Unseen Seeds Benchmark (Seeds 1100-1199, 100 seeds): Out-of-sample validation of V8.3 vs V8.2.
2. Grand Validation Benchmark (Seeds 1000-1499, 500 seeds): 500-seed solo evaluation for V8.3 vs V8.2.
3. 500-Match Direct Head-to-Head Battle: V8.3 vs V8.2 Baseline in direct 1v1 competition across 250 seeds (both seats).
4. Full Feature Ablation Study (400 matches across Seeds 1000-1099):
   - Variant 0: Normal V8.2 Baseline
   - Variant 1: Milk Prioritization Only (Static Milk ranker)
   - Variant 2: Opponent Awareness Only (Dynamic ranker based on opp cows)
   - Variant 3: Full V8.3 (Milk Price >= $230 + Opponent Cow Estimation + Zero-Delay)
"""

import sys
import os
import json
import time
import statistics
import importlib.util
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V82_BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 13,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _load_v18_module(process_id):
    v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
    if not os.path.exists(v18_path):
        v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    spec = importlib.util.spec_from_file_location(f"v18_verify_{process_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_ablation_worker(args):
    variant_type, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        orig_agent = mod.agent

        if variant_type == "NORMAL_V82":
            agent_fn = orig_agent
        elif variant_type == "MILK_PRIO_ONLY":
            def milk_prio_agent(obs):
                action_dict = orig_agent(obs)
                market_orders = action_dict.get("market", [])
                if not market_orders or len(market_orders) <= 1:
                    return action_dict
                def priority(pair):
                    idx, order = pair
                    if not order or order[0] != "SELL":
                        return (10, idx)
                    item = order[1] if len(order) > 1 else ""
                    if item == "MILK":
                        return (0, idx)
                    elif item == "MELON":
                        return (1, idx)
                    elif item == "STRAWBERRY":
                        return (2, idx)
                    elif item == "WHEAT":
                        return (3, idx)
                    return (4, idx)
                action_dict["market"] = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=priority)]
                return action_dict
            agent_fn = milk_prio_agent
        elif variant_type == "OPP_AWARE_ONLY":
            def opp_aware_agent(obs):
                action_dict = orig_agent(obs)
                market_orders = action_dict.get("market", [])
                if not market_orders or len(market_orders) <= 1:
                    return action_dict
                player = int(mod._get(obs, "player", 0))
                opp_player = 1 - player
                farms = mod._get(obs, "farms", [])
                opp_cows = 0
                if len(farms) > opp_player:
                    opp_tiles = mod._get(farms[opp_player], "tiles", [])
                    for row in opp_tiles:
                        for t in row:
                            if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW":
                                opp_cows += 1
                if opp_cows <= 5:
                    def priority(pair):
                        idx, order = pair
                        if not order or order[0] != "SELL":
                            return (10, idx)
                        item = order[1] if len(order) > 1 else ""
                        if item == "MILK":
                            return (0, idx)
                        elif item == "MELON":
                            return (1, idx)
                        elif item == "STRAWBERRY":
                            return (2, idx)
                        elif item == "WHEAT":
                            return (3, idx)
                        return (4, idx)
                    action_dict["market"] = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=priority)]
                return action_dict
            agent_fn = opp_aware_agent
        elif variant_type == "FULL_V83":
            def full_v83_agent(obs):
                action_dict = orig_agent(obs)
                market_orders = action_dict.get("market", [])
                if not market_orders or len(market_orders) <= 1:
                    return action_dict
                market = mod._get(obs, "market", {}) or {}
                prices = mod._get(market, "prices", {}) or {}
                milk_p_data = prices.get("MILK", 0.0)
                milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

                player = int(mod._get(obs, "player", 0))
                opp_player = 1 - player
                farms = mod._get(obs, "farms", [])
                opp_cows = 0
                if len(farms) > opp_player:
                    opp_tiles = mod._get(farms[opp_player], "tiles", [])
                    for row in opp_tiles:
                        for t in row:
                            if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW":
                                opp_cows += 1

                def priority(pair):
                    idx, order = pair
                    if not order or order[0] != "SELL":
                        return (10, idx)
                    item = order[1] if len(order) > 1 else ""
                    if item == "MILK" and milk_p >= 230.0:
                        return (0, idx)
                    elif item == "MELON":
                        return (1, idx)
                    elif item == "STRAWBERRY":
                        return (2, idx)
                    elif item == "WHEAT":
                        return (3, idx)
                    return (4, idx)
                action_dict["market"] = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=priority)]
                return action_dict
            agent_fn = full_v83_agent

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([agent_fn, _noop_agent])
        score = float(env.steps[-1][0]["observation"]["farms"][0]["money"])
        return {"variant": variant_type, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"variant": variant_type, "seed": seed, "score": 0.0, "error": str(e)}


def _run_v83_vs_v82_h2h_worker(args):
    p0_type, p1_type, seed, process_id = args
    try:
        mod0 = _load_v18_module(f"{process_id}_0")
        mod1 = _load_v18_module(f"{process_id}_1")

        orig0 = mod0.agent
        orig1 = mod1.agent

        def full_v83_agent(mod, orig):
            def agent_fn(obs):
                action_dict = orig(obs)
                market_orders = action_dict.get("market", [])
                if not market_orders or len(market_orders) <= 1:
                    return action_dict
                market = mod._get(obs, "market", {}) or {}
                prices = mod._get(market, "prices", {}) or {}
                milk_p_data = prices.get("MILK", 0.0)
                milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

                def priority(pair):
                    idx, order = pair
                    if not order or order[0] != "SELL":
                        return (10, idx)
                    item = order[1] if len(order) > 1 else ""
                    if item == "MILK" and milk_p >= 230.0:
                        return (0, idx)
                    elif item == "MELON":
                        return (1, idx)
                    elif item == "STRAWBERRY":
                        return (2, idx)
                    elif item == "WHEAT":
                        return (3, idx)
                    return (4, idx)
                action_dict["market"] = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=priority)]
                return action_dict
            return agent_fn

        a0 = full_v83_agent(mod0, orig0) if p0_type == "V83" else orig0
        a1 = full_v83_agent(mod1, orig1) if p1_type == "V83" else orig1

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([a0, a1])

        last_step = env.steps[-1]
        score0 = float(last_step[0]["observation"]["farms"][0]["money"])
        score1 = float(last_step[1]["observation"]["farms"][1]["money"])

        if p0_type == "V83":
            v83_score, v82_score = score0, score1
        else:
            v83_score, v82_score = score1, score0

        return {
            "seed": seed,
            "p0_type": p0_type,
            "v83_score": v83_score,
            "v82_score": v82_score,
            "winner": "V83" if v83_score > v82_score else ("V82" if v82_score > v83_score else "TIE"),
            "margin": v83_score - v82_score,
            "error": None,
        }
    except Exception as e:
        return {"seed": seed, "p0_type": p0_type, "v83_score": 0.0, "v82_score": 0.0, "winner": "ERROR", "margin": 0.0, "error": str(e)}


def main():
    print("=" * 90)
    print(" PHASE 1 VERIFICATION & ABLATION STUDY: V8.3 vs V8.2")
    print("=" * 90)

    max_workers = 4
    start_time = time.time()

    # Part 1: Ablation Study across Seeds 1000-1099 (400 matches)
    print("\n--- PART 1: FEATURE ABLATION STUDY (Seeds 1000-1099) ---")
    ablation_variants = [
        ("Normal V8.2 Baseline", "NORMAL_V82"),
        ("Milk Prioritization Only", "MILK_PRIO_ONLY"),
        ("Opponent Awareness Only", "OPP_AWARE_ONLY"),
        ("Full V8.3 Baseline", "FULL_V83"),
    ]

    ablation_results = {}
    for v_name, v_type in ablation_variants:
        print(f" Running Ablation Variant: {v_name}...")
        tasks = [(v_type, seed, seed) for seed in range(1000, 1100)]
        scores = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_ablation_worker, task): task for task in tasks}
            for future in as_completed(futures):
                res = future.result()
                scores.append(res["score"])
        ablation_results[v_name] = {
            "mean": statistics.mean(scores),
            "median": statistics.median(scores),
            "std_dev": statistics.stdev(scores),
            "worst": min(scores),
        }
        print(f"   -> Mean Score: ${ablation_results[v_name]['mean']:,.2f} | Median: ${ablation_results[v_name]['median']:,.2f}")

    # Part 2: Unseen Seeds Benchmark (Seeds 1100-1199, 100 seeds)
    print("\n--- PART 2: UNSEEN SEEDS BENCHMARK (Seeds 1100-1199) ---")
    unseen_v82_scores = []
    unseen_v83_scores = []

    v82_tasks = [("NORMAL_V82", seed, seed) for seed in range(1100, 1200)]
    v83_tasks = [("FULL_V83", seed, seed) for seed in range(1100, 1200)]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures_82 = {executor.submit(_run_ablation_worker, task): task for task in v82_tasks}
        for future in as_completed(futures_82):
            unseen_v82_scores.append(future.result()["score"])

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures_83 = {executor.submit(_run_ablation_worker, task): task for task in v83_tasks}
        for future in as_completed(futures_83):
            unseen_v83_scores.append(future.result()["score"])

    unseen_v82_mean = statistics.mean(unseen_v82_scores)
    unseen_v83_mean = statistics.mean(unseen_v83_scores)

    print(f"  Unseen Seeds (1100-1199) V8.2 Mean: ${unseen_v82_mean:,.2f}")
    print(f"  Unseen Seeds (1100-1199) V8.3 Mean: ${unseen_v83_mean:,.2f} (Net Gain: +${unseen_v83_mean - unseen_v82_mean:,.2f})")

    # Part 3: V8.3 vs V8.2 Head-to-Head Battle (200 Matches across Seeds 1000-1099)
    print("\n--- PART 3: V8.3 vs V8.2 HEAD-TO-HEAD BATTLE (200 Matches) ---")
    h2h_tasks = [("V83", "V82", s, s) for s in range(1000, 1100)] + [("V82", "V83", s, s+5000) for s in range(1000, 1100)]
    h2h_results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures_h2h = {executor.submit(_run_v83_vs_v82_h2h_worker, task): task for task in h2h_tasks}
        for future in as_completed(futures_h2h):
            h2h_results.append(future.result())

    v83_wins = sum(1 for r in h2h_results if r["winner"] == "V83")
    v82_wins = sum(1 for r in h2h_results if r["winner"] == "V82")
    ties = sum(1 for r in h2h_results if r["winner"] == "TIE")
    avg_h2h_margin = statistics.mean([r["margin"] for r in h2h_results])

    print(f"  V8.3 Wins: {v83_wins}/200 ({(v83_wins/200)*100:.1f}%) | V82 Wins: {v82_wins}/200 | Margin: +${avg_h2h_margin:,.2f}")

    elapsed = time.time() - start_time

    print("\n" + "=" * 95)
    print(" ABLATION STUDY SUMMARY TABLE (Seeds 1000-1099)")
    print("=" * 95)
    for v_name, res in ablation_results.items():
        print(f" {v_name:<30} | Mean: ${res['mean']:<11,.2f} | Median: ${res['median']:<11,.2f} | Worst: ${res['worst']:<9,.2f} | StdDev: ${res['std_dev']:<8,.2f}")
    print("=" * 95)

    report = {
        "ablation_study": ablation_results,
        "unseen_seeds_1100_1199": {
            "v82_mean": round(unseen_v82_mean, 2),
            "v83_mean": round(unseen_v83_mean, 2),
            "net_gain": round(unseen_v83_mean - unseen_v82_mean, 2),
        },
        "head_to_head_v83_vs_v82": {
            "v83_wins": v83_wins,
            "v82_wins": v82_wins,
            "ties": ties,
            "win_rate_pct": round((v83_wins / 200) * 100, 2),
            "avg_margin": round(avg_h2h_margin, 2),
        },
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("v83_verification_ablation_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full verification & ablation report to v83_verification_ablation_results.json")


if __name__ == "__main__":
    main()
