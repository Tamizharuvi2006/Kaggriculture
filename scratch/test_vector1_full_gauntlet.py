import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc4_1_clean as rc41_mod
from scratch.test_vector1_persistence import run_persistence_variant, path_arao, path_soumi

replays = [
    ("episode-104475527-replay.json", "RicardoLopez (1052 Elo)"),
    ("episode-104424149-replay.json", "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", "Soumi Ghosh"),
    ("episode-104379472-replay.json", "arao"),
]

low_seeds = [
    (628719714, "Ep 105112452 ($29k Floor)"),
    (334330253, "Ep 105105439 ($38k vs zZx Hee)"),
    (652661405, "Ep 105107201 ($46k vs 623 Elo)"),
    (264913612, "Ep 105116829 ($57k)"),
    (1064891062, "Ep 105104584 ($73k vs 113k)"),
]

print("=" * 115)
print("VECTOR 1: 1-TICK CONTROL vs 2-HOUR PERSISTENCE (ALL 20 MATCHES)")
print("=" * 115)
print(f"{'MATCH / OPPONENT':<28} | {'SEAT':<4} | {'1-TICK SCORE':>12} | {'2-HR SCORE':>12} | {'DELTA':>10} | {'1-TICK CONF':>11} | {'2-HR CONF':>11}")
print("-" * 115)

diffs = []
for r_name, opp_label in replays:
    p = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    for seat in (0, 1):
        r1 = run_persistence_variant("1-tick", replay_path=p, seat=seat)
        r2 = run_persistence_variant("2-hours", replay_path=p, seat=seat)
        d = r2["score"] - r1["score"]
        diffs.append(d)
        c1_str = f"D{r1['confirm_day']} H{r1['confirm_hour']}" if r1['confirm_day'] else "NO"
        c2_str = f"D{r2['confirm_day']} H{r2['confirm_hour']}" if r2['confirm_day'] else "NO"
        print(f"{opp_label:<28} | S{seat}  | ${r1['score']:>11,.0f} | ${r2['score']:>11,.0f} | ${d:>+9,.0f} | {c1_str:>11} | {c2_str:>11}")

for s_val, label in low_seeds:
    for seat in (0, 1):
        r1 = run_persistence_variant("1-tick", seed_val=s_val, seat=seat)
        r2 = run_persistence_variant("2-hours", seed_val=s_val, seat=seat)
        d = r2["score"] - r1["score"]
        diffs.append(d)
        c1_str = f"D{r1['confirm_day']} H{r1['confirm_hour']}" if r1['confirm_day'] else "NO"
        c2_str = f"D{r2['confirm_day']} H{r2['confirm_hour']}" if r2['confirm_day'] else "NO"
        print(f"{label:<28} | S{seat}  | ${r1['score']:>11,.0f} | ${r2['score']:>11,.0f} | ${d:>+9,.0f} | {c1_str:>11} | {c2_str:>11}")

print("=" * 115)
print(f"Total Matches: 20 | Identical Matches: {sum(1 for x in diffs if x == 0)}/20 | Mean Delta: ${sum(diffs)/len(diffs):>+,.2f}")
print("=" * 115)
