"""Head-to-Head Battle: V8.3 Champion Baseline vs V4.1 Base Engine.

Executes direct 1v1 battle across 20 benchmark seeds (Seeds 1000-1019)
to compare final scores, win rates, and average victory margins.
"""

import sys
import os
import json
import statistics
import importlib.util
import kaggle_environments

sys.path.insert(0, os.path.dirname(__file__))

# Load V8.3 Standalone Champion
V83_PATH = r"D:\kaggriculture\baseline\submission_v83_standalone.py"
spec83 = importlib.util.spec_from_file_location("v83_h2h_v41", V83_PATH)
v83_mod = importlib.util.module_from_spec(spec83)
spec83.loader.exec_module(v83_mod)

# Load V18 Base Engine
V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
spec18 = importlib.util.spec_from_file_location("v18_base_h2h", V18_PATH)
v18_mod = importlib.util.module_from_spec(spec18)
spec18.loader.exec_module(v18_mod)

def main():
    print("=" * 90)
    print(" HEAD-TO-HEAD BATTLE: V8.3 CHAMPION vs V4.1 BASE ENGINE (20 Seeds)")
    print("=" * 90)

    v83_scores = []
    v41_scores = []
    results = []

    for seed in range(1000, 1020):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state = env.run([v83_mod.agent, v18_mod.agent])
        s83 = float(state[-1][0]["observation"]["farms"][0]["money"])
        s41 = float(state[-1][1]["observation"]["farms"][1]["money"])

        v83_scores.append(s83)
        v41_scores.append(s41)
        winner = "V8.3" if s83 > s41 else ("V4.1" if s41 > s83 else "TIE")
        print(f" Seed {seed}: V8.3 = ${s83:,.2f} | V4.1 = ${s41:,.2f} | Winner: {winner}")

    v83_wins = sum(1 for s83, s41 in zip(v83_scores, v41_scores) if s83 > s41)
    v41_wins = sum(1 for s83, s41 in zip(v83_scores, v41_scores) if s41 > s83)
    ties = sum(1 for s83, s41 in zip(v83_scores, v41_scores) if s83 == s41)

    mean_83 = statistics.mean(v83_scores)
    mean_41 = statistics.mean(v41_scores)
    margin = mean_83 - mean_41

    print("\n" + "=" * 90)
    print(" BATTLE SUMMARY: V8.3 vs V4.1 BASE ENGINE")
    print("=" * 90)
    print(f" V8.3 Champion Wins:    {v83_wins} / 20 ({(v83_wins/20)*100:.1f}%)")
    print(f" V4.1 Base Engine Wins:  {v41_wins} / 20 ({(v41_wins/20)*100:.1f}%)")
    print(f" Ties / Equal Scores:    {ties} / 20")
    print("-" * 90)
    print(f" V8.3 Avg Final Score:  ${mean_83:,.2f}")
    print(f" V4.1 Avg Final Score:  ${mean_41:,.2f}")
    print(f" Victory Margin:        +${margin:,.2f} per match in favor of V8.3 Champion")
    print("=" * 90)

    report = {
        "v83_wins": v83_wins,
        "v41_wins": v41_wins,
        "ties": ties,
        "v83_mean_score": round(mean_83, 2),
        "v41_mean_score": round(mean_41, 2),
        "victory_margin": round(margin, 2),
    }
    with open("v83_vs_v41_battle_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
