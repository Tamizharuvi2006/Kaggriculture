"""Research 19.5: 100-Match Robustness Check (Cows=12 vs Cows=13).

Evaluates Cows=12 (Baseline V8.1) vs Cows=13 across the full 100 official benchmark matches (Seeds 1000-1099; 200 total matches).

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Peak Score ($)
- Standard Deviation ($)
- Bankruptcy / Collapse Count (<$10k final score)
- Avg Idle Workers / Turn
"""

import sys
import os
import json
import importlib.util
import statistics
import time

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_robust", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def run_100_match_robustness(seeds=list(range(1000, 1100))):
    print("=" * 85)
    print(f" RESEARCH 19.5: 100-MATCH ROBUSTNESS CHECK (Seeds 1000-1099; {len(seeds)*2} Matches)")
    print("=" * 85)

    configs = [
        {"label": "Baseline V8.1 (Cows=12)", "cows": 12},
        {"label": "Variant A (Cows=13)", "cows": 13},
    ]

    results = []

    for cfg in configs:
        label = cfg["label"]
        cow_num = cfg["cows"]

        print(f"\n--- Running {label} across {len(seeds)} official seeds ---")

        strat = dict(BASE_STRATEGY)
        strat["cows"] = cow_num

        scores = []
        idle_worker_turns = []
        bankruptcies = 0

        start_time = time.time()

        for idx, seed in enumerate(seeds):
            v18_mod.configure_strategy(dict(strat))

            match_idle = 0

            def tracking_agent(obs):
                nonlocal match_idle

                action_dict = v18_mod.agent(obs)
                farmer_act = action_dict.get("farmer", ["PASS"])
                hands_acts = action_dict.get("hands", [])
                all_acts = [farmer_act] + hands_acts

                for act in all_acts:
                    if not act or act == ["PASS"]:
                        match_idle += 1

                return action_dict

            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            state = env.run([tracking_agent, _noop_agent])

            final_score = state[-1][0]["reward"]
            scores.append(final_score)
            idle_worker_turns.append(match_idle / 720.0)

            if final_score < 10000.0:
                bankruptcies += 1

            if (idx + 1) % 25 == 0 or idx == len(seeds) - 1:
                print(f"  [Progress {idx+1}/{len(seeds)}] Current Mean: ${statistics.mean(scores):,.2f}")

        elapsed = time.time() - start_time
        avg_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores)
        worst_score = min(scores)
        best_score = max(scores)
        avg_idle = statistics.mean(idle_worker_turns)

        res = {
            "label": label,
            "cows": cow_num,
            "seeds_evaluated": len(seeds),
            "avg_score": round(avg_score, 2),
            "median_score": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "worst_score": round(worst_score, 2),
            "best_score": round(best_score, 2),
            "bankruptcies": bankruptcies,
            "avg_idle_workers_per_turn": round(avg_idle, 2),
            "elapsed_seconds": round(elapsed, 1),
            "scores": scores,
        }

        results.append(res)
        print(f"  Completed {label} in {elapsed:.1f}s!")
        print(f"  Avg Score: ${avg_score:,.2f} | Median: ${median_score:,.2f} | StdDev: ${std_score:,.2f}")
        print(f"  Worst Score: ${worst_score:,.2f} | Best Score: ${best_score:,.2f} | Bankruptcies: {bankruptcies}")

    # Comparative analysis
    b12 = results[0]
    c13 = results[1]
    diff = c13["avg_score"] - b12["avg_score"]

    print("\n" + "=" * 90)
    print(" RESEARCH 19.5: OFFICIAL 100-MATCH COMPARATIVE SUMMARY (Seeds 1000-1099)")
    print("=" * 90)
    print(f"{'Configuration':<25} | {'Avg Score ($)':<13} | {'Median ($)':<11} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 95)
    for r in results:
        print(
            f"{r['label']:<25} | ${r['avg_score']:<12,.2f} | ${r['median_score']:<10,.2f} | ${r['worst_score']:<9,.2f} | ${r['std_dev']:<8,.2f} | {r['bankruptcies']:<12}"
        )
    print("=" * 90)

    if diff > 500 and c13["bankruptcies"] == 0:
        conclusion = f"Cows=13 CONFIRMED ROBUST OVER 100 SEEDS (+${diff:,.2f} gain vs Cows=12). Ready to promote to frozen baseline!"
    elif diff <= 500 and diff >= -500:
        conclusion = f"Cows=13 and Cows=12 are statistically equivalent (+${diff:,.2f} diff over 100 seeds). Score gain was sample variance."
    else:
        conclusion = f"Cows=12 is superior over 100 seeds (-${abs(diff):,.2f} drop for Cows=13)."

    print(f"\nFINAL VERDICT: {conclusion}\n")

    report = {
        "results": results,
        "net_difference_c13_vs_c12": round(diff, 2),
        "final_verdict": conclusion,
    }

    with open("research19_5_robustness_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full 100-match report to research19_5_robustness_results.json")

    return report


if __name__ == "__main__":
    run_100_match_robustness()
