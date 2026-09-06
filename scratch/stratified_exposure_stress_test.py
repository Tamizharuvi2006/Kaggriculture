import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_rc3_h6 as rc3_mod

# Let's run a clean 10-seed paired gauntlet on unseen seeds 101 to 110 (20 games total)
# Each seed is played in Seat 0 and Seat 1 (Seat-Swapped Control)
test_seeds = list(range(101, 111))

def run_paired_game(seed):
    # Match 1: Seat 0 = RC3, Seat 1 = RC2
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    opp_straw_m1 = {0: 0, 1: 0}
    for s in range(720):
        if env1.done: break
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        if obs0.day == 11 and obs0.hour == 0:
            opp_straw_m1[0] = sum(1 for r in obs0.farms[1].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_straw_m1[1] = sum(1 for r in obs1.farms[0].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        act0 = rc3_mod.agent(obs0)
        act1 = rc2_mod.agent(obs1)
        env1.step([act0, act1])
    score_rc3_s0 = env1.state[0].observation.farms[0].money
    score_rc2_s1 = env1.state[1].observation.farms[1].money

    # Match 2: Seat 0 = RC2, Seat 1 = RC3
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    opp_straw_m2 = {0: 0, 1: 0}
    for s in range(720):
        if env2.done: break
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        if obs0.day == 11 and obs0.hour == 0:
            opp_straw_m2[0] = sum(1 for r in obs0.farms[1].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_straw_m2[1] = sum(1 for r in obs1.farms[0].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        act0 = rc2_mod.agent(obs0)
        act1 = rc3_mod.agent(obs1)
        env2.step([act0, act1])
    score_rc2_s0 = env2.state[0].observation.farms[0].money
    score_rc3_s1 = env2.state[1].observation.farms[1].money

    return {
        "seed": seed,
        "m1": {"rc3": score_rc3_s0, "rc2": score_rc2_s1, "opp_straw": opp_straw_m1[0]},
        "m2": {"rc3": score_rc3_s1, "rc2": score_rc2_s0, "opp_straw": opp_straw_m2[1]},
    }

print("=" * 115)
print("PHASE-11 UNSEEN SEED STRESS TEST: RC2 CONTROL vs RC3-H6 (SEEDS 101-110, 20 MATCHES)")
print("=" * 115)
print(f"{'SEED':<8} | {'MATCHUP':<12} | {'OPP STRAW D11':>15} | {'RC3 SCORE':>14} | {'RC2 SCORE':>14} | {'DIFF (RC3 - RC2)':>18}")
print("-" * 115)

results = []
for sd in test_seeds:
    res = run_paired_game(sd)
    results.append(res)
    m1 = res["m1"]
    m2 = res["m2"]
    print(f"{sd:<8} | {'M1 (RC3 S0)':<12} | {m1['opp_straw']:>15} | ${m1['rc3']:>13,.0f} | ${m1['rc2']:>13,.0f} | ${m1['rc3']-m1['rc2']:>+17,.0f}")
    print(f"{sd:<8} | {'M2 (RC3 S1)':<12} | {m2['opp_straw']:>15} | ${m2['rc3']:>13,.0f} | ${m2['rc2']:>13,.0f} | ${m2['rc3']-m2['rc2']:>+17,.0f}")
    sys.stdout.flush()

print("=" * 115)

rc3_all = [r["m1"]["rc3"] for r in results] + [r["m2"]["rc3"] for r in results]
rc2_all = [r["m1"]["rc2"] for r in results] + [r["m2"]["rc2"] for r in results]

diffs = [rc3_all[i] - rc2_all[i] for i in range(len(rc3_all))]
wins = sum(1 for d in diffs if d > 0)
losses = sum(1 for d in diffs if d < 0)
ties = sum(1 for d in diffs if d == 0)

print(f"{'Mean Score':<30} | RC3: ${sum(rc3_all)/len(rc3_all):>10,.0f} | RC2: ${sum(rc2_all)/len(rc2_all):>10,.0f} | Diff: ${sum(rc3_all)/len(rc3_all) - sum(rc2_all)/len(rc2_all):>+10,.0f}")
print(f"{'Floor Score (Minimum)':<30} | RC3: ${min(rc3_all):>10,.0f} | RC2: ${min(rc2_all):>10,.0f} | Diff: ${min(rc3_all) - min(rc2_all):>+10,.0f}")
print(f"{'Ceiling Score (Maximum)':<30} | RC3: ${max(rc3_all):>10,.0f} | RC2: ${max(rc2_all):>10,.0f} | Diff: ${max(rc3_all) - max(rc2_all):>+10,.0f}")
print(f"Head-to-Head (20 Games): RC3 Wins: {wins} | RC2 Wins: {losses} | Ties: {ties}")
print("=" * 115)

with open("reports/RC3_UNSEEN_SEEDS_STRESS_TEST.json", "w") as f:
    json.dump({
        "seeds": test_seeds,
        "rc3_scores": rc3_all,
        "rc2_scores": rc2_all,
        "diffs": diffs,
        "summary": {
            "rc3_mean": sum(rc3_all)/len(rc3_all), "rc2_mean": sum(rc2_all)/len(rc2_all),
            "rc3_floor": min(rc3_all), "rc2_floor": min(rc2_all),
            "rc3_ceiling": max(rc3_all), "rc2_ceiling": max(rc2_all),
            "wins": wins, "losses": losses, "ties": ties
        }
    }, f, indent=2)
print("Complete audit saved to reports/RC3_UNSEEN_SEEDS_STRESS_TEST.json")
