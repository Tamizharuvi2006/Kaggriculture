import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_h6_threshold16 as h6_mod

# Let's test across 6 diverse unseen seeds (Seeds 501, 502, 503, 504, 505, 506)
# Each with seat-swapped paired controls (12 games total)
seeds = [501, 502, 503, 504, 505, 506]

def run_paired_matchup(seed):
    # Match 1: Seat 0 = H6, Seat 1 = RC2
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
        act0 = h6_mod.agent(obs0)
        act1 = rc2_mod.agent(obs1)
        env1.step([act0, act1])
    score_h6_s0 = env1.state[0].observation.farms[0].money
    score_rc2_s1 = env1.state[1].observation.farms[1].money

    # Match 2: Seat 0 = RC2, Seat 1 = H6
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
        act1 = h6_mod.agent(obs1)
        env2.step([act0, act1])
    score_rc2_s0 = env2.state[0].observation.farms[0].money
    score_h6_s1 = env2.state[1].observation.farms[1].money

    return {
        "seed": seed,
        "m1": {"h6": score_h6_s0, "rc2": score_rc2_s1, "opp_straw": opp_straw_m1[0]},
        "m2": {"h6": score_h6_s1, "rc2": score_rc2_s0, "opp_straw": opp_straw_m2[1]},
    }

print("=" * 105)
print("STRATIFIED UNSEEN SEED VALIDATION: RC2 CONTROL vs H6-THRESHOLD16 (SEEDS 501-506)")
print("=" * 105)
print(f"{'SEED':<8} | {'MATCHUP':<12} | {'OPP STRAW D11':>15} | {'H6 SCORE':>14} | {'RC2 SCORE':>14} | {'DIFF (H6 - RC2)':>18}")
print("-" * 105)

results = []
for sd in seeds:
    res = run_paired_matchup(sd)
    results.append(res)
    m1 = res["m1"]
    m2 = res["m2"]
    print(f"{sd:<8} | {'M1 (H6 S0)':<12} | {m1['opp_straw']:>15} | ${m1['h6']:>13,.0f} | ${m1['rc2']:>13,.0f} | ${m1['h6']-m1['rc2']:>+17,.0f}")
    print(f"{sd:<8} | {'M2 (H6 S1)':<12} | {m2['opp_straw']:>15} | ${m2['h6']:>13,.0f} | ${m2['rc2']:>13,.0f} | ${m2['h6']-m2['rc2']:>+17,.0f}")
    sys.stdout.flush()

print("=" * 105)

h6_all = [r["m1"]["h6"] for r in results] + [r["m2"]["h6"] for r in results]
rc2_all = [r["m1"]["rc2"] for r in results] + [r["m2"]["rc2"] for r in results]

print(f"Unseen Seeds Mean Score: H6: ${sum(h6_all)/len(h6_all):,.0f} vs RC2: ${sum(rc2_all)/len(rc2_all):,.0f} (Diff: ${sum(h6_all)/len(h6_all) - sum(rc2_all)/len(rc2_all):+,.0f})")
print(f"Unseen Seeds Floor:      H6: ${min(h6_all):,.0f} vs RC2: ${min(rc2_all):,.0f} (Diff: ${min(h6_all) - min(rc2_all):+,.0f})")
print(f"Unseen Seeds Ceiling:    H6: ${max(h6_all):,.0f} vs RC2: ${max(rc2_all):,.0f} (Diff: ${max(h6_all) - max(rc2_all):+,.0f})")
print("=" * 105)
