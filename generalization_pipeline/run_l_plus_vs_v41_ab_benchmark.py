"""Controlled Paired A/B Benchmark: Candidate L+ vs Frozen V4.1 Master.

Evaluates Candidate L+ vs Frozen V4.1 across 200 Paired Matches on Seeds 3000-3049:
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
from concurrent.futures import ProcessPoolExecutor
from scipy import stats

import kaggle_environments


import importlib.util

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

def _load_v18_module():
    spec = importlib.util.spec_from_file_location("v18_arch_mod", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Opponent Archetypes
def capital_turtle_agent(obs, configuration=None):
    mod = _load_v18_module()
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })
    return mod.agent(obs)


def cattle_rusher_agent(obs, configuration=None):
    mod = _load_v18_module()
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "cows": 12,
        "opening_melons": 15,
    })
    return mod.agent(obs)


def market_manipulator_agent(obs, configuration=None):
    mod = _load_v18_module()
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": False,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent(obs)


def crop_expansionist_agent(obs, configuration=None):
    mod = _load_v18_module()
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "land_ne_day": 4,
        "strawberries": 50,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent(obs)


ARCHETYPES = {
    "Capital_Turtle": capital_turtle_agent,
    "Cattle_Rusher": cattle_rusher_agent,
    "Market_Manipulator": market_manipulator_agent,
    "Crop_Expansionist": crop_expansionist_agent,
}


def _run_single_seed_paired_benchmark(args):
    import sys
    import os
    if r"D:\kaggriculture" not in sys.path:
        sys.path.insert(0, r"D:\kaggriculture")

    archetype_name, seed = args
    opp_agent = ARCHETYPES[archetype_name]

    # Import bot agents isolated per process
    import importlib.util
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    spec_v41 = importlib.util.spec_from_file_location("v41_mod_worker", v18_path)
    v41_mod = importlib.util.module_from_spec(spec_v41)
    spec_v41.loader.exec_module(v41_mod)

    lplus_path = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"
    spec_lplus = importlib.util.spec_from_file_location("lplus_mod_worker", lplus_path)
    l_plus_mod = importlib.util.module_from_spec(spec_lplus)
    spec_lplus.loader.exec_module(l_plus_mod)

    # Configure V4.1 Frozen Ground Truth
    v41_mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })

    # Run Match 1: Candidate L+ vs Opponent O on Seed S
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state1 = env1.run([l_plus_mod.agent, opp_agent])
    lplus_wealth = state1[-1][0]["observation"]["farms"][0]["money"]
    opp1_wealth = state1[-1][1]["observation"]["farms"][1]["money"]

    # Run Match 2: Frozen V4.1 vs Opponent O on Seed S
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state2 = env2.run([v41_mod.agent, opp_agent])
    v41_wealth = state2[-1][0]["observation"]["farms"][0]["money"]
    opp2_wealth = state2[-1][1]["observation"]["farms"][1]["money"]

    # Run Match 3: Direct Head-to-Head Candidate L+ vs Frozen V4.1 on Seed S
    env3 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state3 = env3.run([l_plus_mod.agent, v41_mod.agent])
    direct_lplus_wealth = state3[-1][0]["observation"]["farms"][0]["money"]
    direct_v41_wealth = state3[-1][1]["observation"]["farms"][1]["money"]

    delta = lplus_wealth - v41_wealth

    return {
        "archetype": archetype_name,
        "seed": seed,
        "lplus_wealth": lplus_wealth,
        "v41_wealth": v41_wealth,
        "delta": delta,
        "lplus_won_vs_opp": lplus_wealth > opp1_wealth,
        "v41_won_vs_opp": v41_wealth > opp2_wealth,
        "direct_lplus_wealth": direct_lplus_wealth,
        "direct_v41_wealth": direct_v41_wealth,
        "direct_lplus_won": direct_lplus_wealth > direct_v41_wealth,
        "lplus_catastrophic": lplus_wealth < 10000,
        "v41_catastrophic": v41_wealth < 10000,
    }


def main():
    print("=" * 95)
    print(" CONTROLLED PAIRED A/B BENCHMARK: CANDIDATE L+ VS FROZEN V4.1 MASTER")
    print("=" * 95)
    print(" Launching 200 Paired Matches across 4 Process Workers (Seeds 3000-3049)...")

    tasks = []
    seeds = range(3000, 3050)  # 50 seeds per archetype = 200 paired matches
    for arch_name in ARCHETYPES:
        for seed in seeds:
            tasks.append((arch_name, seed))

    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_run_single_seed_paired_benchmark, tasks))

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
    print(" PAIRED A/B RESULTS BY OPPONENT ARCHETYPE (50 SEEDS EACH)")
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

        # Calculate t-test p-value
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

    # Overall t-test
    all_lplus_w = [r["lplus_wealth"] for r in results]
    all_v41_w = [r["v41_wealth"] for r in results]
    overall_t, overall_p = stats.ttest_rel(all_lplus_w, all_v41_w)

    print("=" * 95)
    print(f" OVERALL COMBINED BENCHMARK (200 PAIRED MATCHES):")
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
