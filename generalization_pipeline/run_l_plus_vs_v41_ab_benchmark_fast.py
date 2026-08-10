"""Fast Controlled Paired A/B Benchmark: Candidate L+ vs Frozen V4.1 Master.

Evaluates Candidate L+ vs Frozen V4.1 across 100 Paired Matches on Seeds 3000-3024 (25 paired matches per archetype):
For every seed S and opponent archetype O:
- Match 1: Candidate L+ vs Opponent O on Seed S
- Match 2: Frozen V4.1 vs Opponent O on Seed S
- Direct Match: Candidate L+ vs Frozen V4.1 on Seed S

Computes exact paired wealth deltas: Delta = Wealth(L+) - Wealth(V4.1)
"""

import sys
import os
import json
import math
import importlib.util
from concurrent.futures import ProcessPoolExecutor
from scipy import stats

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
LPLUS_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"


def _worker_process_batch(task_batch):
    if r"D:\kaggriculture" not in sys.path:
        sys.path.insert(0, r"D:\kaggriculture")

    import kaggle_environments

    spec_v41 = importlib.util.spec_from_file_location("v41_batch_mod", V18_PATH)
    v41_mod = importlib.util.module_from_spec(spec_v41)
    spec_v41.loader.exec_module(v41_mod)

    spec_lplus = importlib.util.spec_from_file_location("lplus_batch_mod", LPLUS_PATH)
    l_plus_mod = importlib.util.module_from_spec(spec_lplus)
    spec_lplus.loader.exec_module(l_plus_mod)

    batch_results = []
    for archetype_name, seed in task_batch:
        # Construct archetype agent
        def get_opp_agent(arch_name):
            spec = importlib.util.spec_from_file_location("opp_mod", V18_PATH)
            opp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(opp_mod)
            if arch_name == "Capital_Turtle":
                opp_mod.configure_strategy({"use_fixed_schedule": False, "v13_market_adaptation": True, "opening_melons": 10, "cows": 8})
            elif arch_name == "Cattle_Rusher":
                opp_mod.configure_strategy({"use_fixed_schedule": False, "cows": 12, "opening_melons": 15})
            elif arch_name == "Market_Manipulator":
                opp_mod.configure_strategy({"use_fixed_schedule": False, "v13_market_adaptation": False, "opening_melons": 15, "cows": 8})
            elif arch_name == "Crop_Expansionist":
                opp_mod.configure_strategy({"use_fixed_schedule": False, "land_ne_day": 4, "strawberries": 50, "opening_melons": 15, "cows": 8})
            return opp_mod.agent

        opp_agent = get_opp_agent(archetype_name)

        # Configure V4.1 Frozen Ground Truth
        v41_mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })

        # Match 1: Candidate L+ vs Opponent O
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state1 = env1.run([l_plus_mod.agent, opp_agent])
        lplus_w = state1[-1][0]["observation"]["farms"][0]["money"]
        opp1_w = state1[-1][1]["observation"]["farms"][1]["money"]

        # Match 2: Frozen V4.1 vs Opponent O
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state2 = env2.run([v41_mod.agent, opp_agent])
        v41_w = state2[-1][0]["observation"]["farms"][0]["money"]
        opp2_w = state2[-1][1]["observation"]["farms"][1]["money"]

        # Match 3: Direct Head-to-Head Candidate L+ vs Frozen V4.1
        env3 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state3 = env3.run([l_plus_mod.agent, v41_mod.agent])
        dir_lplus_w = state3[-1][0]["observation"]["farms"][0]["money"]
        dir_v41_w = state3[-1][1]["observation"]["farms"][1]["money"]

        delta = lplus_w - v41_w
        batch_results.append({
            "archetype": archetype_name,
            "seed": seed,
            "lplus_wealth": lplus_w,
            "v41_wealth": v41_w,
            "delta": delta,
            "lplus_won_vs_opp": lplus_w > opp1_w,
            "v41_won_vs_opp": v41_w > opp2_w,
            "direct_lplus_wealth": dir_lplus_w,
            "direct_v41_wealth": dir_v41_w,
            "direct_lplus_won": dir_lplus_w > dir_v41_w,
            "lplus_catastrophic": lplus_w < 10000,
            "v41_catastrophic": v41_w < 10000,
        })
    return batch_results


def main():
    print("=" * 95)
    print(" CONTROLLED PAIRED A/B BENCHMARK: CANDIDATE L+ VS FROZEN V4.1 MASTER")
    print("=" * 95)
    print(" Launching 100 Paired Matches across 4 Fast Process Workers (Seeds 3000-3024)...")

    archetypes = ["Capital_Turtle", "Cattle_Rusher", "Market_Manipulator", "Crop_Expansionist"]
    seeds = range(3000, 3025)  # 25 seeds per archetype = 100 paired matches

    all_tasks = []
    for arch in archetypes:
        for s in seeds:
            all_tasks.append((arch, s))

    num_workers = 4
    chunk_size = math.ceil(len(all_tasks) / num_workers)
    batches = [all_tasks[i:i + chunk_size] for i in range(0, len(all_tasks), chunk_size)]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        batch_outputs = list(executor.map(_worker_process_batch, batches))

    results = []
    for b in batch_outputs:
        results.extend(b)

    # Aggregate by Archetype
    archetype_summary = {}
    all_deltas = []
    all_direct_lplus_wins = 0
    all_direct_matches = len(results)

    for record in results:
        arch = record["archetype"]
        if arch not in archetype_summary:
            archetype_summary[arch] = {
                "records": [],
                "deltas": [],
                "lplus_wealths": [],
                "v41_wealths": [],
                "lplus_wins_opp": 0,
                "v41_wins_opp": 0,
                "direct_lplus_wins": 0,
                "lplus_catastrophic": 0,
                "v41_catastrophic": 0,
            }

        s = archetype_summary[arch]
        s["records"].append(record)
        s["deltas"].append(record["delta"])
        s["lplus_wealths"].append(record["lplus_wealth"])
        s["v41_wealths"].append(record["v41_wealth"])
        if record["lplus_won_vs_opp"]:
            s["lplus_wins_opp"] += 1
        if record["v41_won_vs_opp"]:
            s["v41_wins_opp"] += 1
        if record["direct_lplus_won"]:
            s["direct_lplus_wins"] += 1
            all_direct_lplus_wins += 1
        if record["lplus_catastrophic"]:
            s["lplus_catastrophic"] += 1
        if record["v41_catastrophic"]:
            s["v41_catastrophic"] += 1

        all_deltas.append(record["delta"])

    print("\n" + "=" * 95)
    print(" PAIRED A/B RESULTS BY OPPONENT ARCHETYPE (25 SEEDS EACH)")
    print("=" * 95)
    print(f"{'Archetype':<20} | {'Direct Win %':<12} | {'L+ Avg ($)':<12} | {'V4.1 Avg ($)':<12} | {'Mean Delta ($)':<15} | {'p-value':<10} | {'Status'}")
    print("-" * 95)

    final_report = []

    for arch, s in archetype_summary.items():
        n = len(s["records"])
        mean_lplus = sum(s["lplus_wealths"]) / n
        mean_v41 = sum(s["v41_wealths"]) / n
        mean_delta = sum(s["deltas"]) / n
        direct_wr = (s["direct_lplus_wins"] / n) * 100.0

        t_stat, p_val = stats.ttest_rel(s["lplus_wealths"], s["v41_wealths"])
        status = "PASS (L+ > V4.1)" if mean_delta > 0 and p_val < 0.05 else "TIED / WEAK" if p_val >= 0.05 else "FAIL"

        print(f"{arch:<20} | {direct_wr:5.1f}%       | ${mean_lplus:10.2f} | ${mean_v41:10.2f} | +${mean_delta:12.2f} | {p_val:8.4f}   | {status}")

        final_report.append({
            "archetype": arch,
            "paired_matches": n,
            "direct_win_rate_lplus_vs_v41": direct_wr,
            "mean_lplus_wealth": mean_lplus,
            "mean_v41_wealth": mean_v41,
            "mean_delta": mean_delta,
            "p_value": p_val,
            "lplus_wins_vs_opp": s["lplus_wins_opp"],
            "v41_wins_vs_opp": s["v41_wins_opp"],
            "lplus_catastrophic": s["lplus_catastrophic"],
            "v41_catastrophic": s["v41_catastrophic"],
        })

    # Total Combined Statistics
    total_n = len(all_deltas)
    overall_mean_delta = sum(all_deltas) / total_n
    sorted_deltas = sorted(all_deltas)
    median_delta = sorted_deltas[total_n // 2]
    min_delta = min(all_deltas)
    max_delta = max(all_deltas)
    overall_direct_wr = (all_direct_lplus_wins / total_n) * 100.0

    all_lplus_w = [r["lplus_wealth"] for r in results]
    all_v41_w = [r["v41_wealth"] for r in results]
    overall_t, overall_p = stats.ttest_rel(all_lplus_w, all_v41_w)

    print("=" * 95)
    print(f" OVERALL COMBINED A/B BENCHMARK (100 PAIRED MATCHES / 300 TOTAL MATCHES):")
    print(f" - Candidate L+ Direct Win Rate vs V4.1: {overall_direct_wr:.1f}% ({all_direct_lplus_wins}/{total_n} Wins)")
    print(f" - Overall Mean Paired Wealth Delta: +${overall_mean_delta:.2f}")
    print(f" - Overall Median Paired Wealth Delta: +${median_delta:.2f}")
    print(f" - Minimum Delta (Worst Case): ${min_delta:.2f}")
    print(f" - Maximum Delta (Best Case): +${max_delta:.2f}")
    print(f" - Paired t-Test p-value: {overall_p:.6e}")
    print("=" * 95)

    # Save JSON Dataset
    output_path = r"D:\kaggriculture\generalization_pipeline\l_plus_vs_v41_paired_ab_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "overall": {
                "total_paired_matches": total_n,
                "direct_lplus_win_rate": overall_direct_wr,
                "mean_delta": overall_mean_delta,
                "median_delta": median_delta,
                "min_delta": min_delta,
                "max_delta": max_delta,
                "p_value": overall_p,
            },
            "archetypes": final_report,
            "raw_records": results,
        }, f, indent=2)

    print(f"\nSaved complete raw A/B dataset to {output_path}")


if __name__ == "__main__":
    main()
