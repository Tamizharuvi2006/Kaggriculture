import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

# Import agents
import submission_rc2_terminal_horizon as rc2_mod
import submission_rc3_h6 as rc3_mod
import submission_rc4_forecast_confirm as rc4_mod

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

def run_single_game(agent_p0, agent_p1, seed, opp_tape=None, max_steps=720):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    straw_rev = {0: 0.0, 1: 0.0}
    other_rev = {0: 0.0, 1: 0.0}
    opp_straw_d11 = {0: 0, 1: 0}
    
    for step in range(max_steps):
        if env.done: break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        day = obs0.day
        hour = obs0.hour
        
        if day == 11 and hour == 0:
            opp_straw_d11[0] = sum(1 for r in obs0.farms[1].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            opp_straw_d11[1] = sum(1 for r in obs1.farms[0].tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            
        if opp_tape is not None and step in opp_tape:
            t0, t1 = opp_tape[step]
            act0 = t0 if t0 is not None else agent_p0(obs0)
            act1 = t1 if t1 is not None else agent_p1(obs1)
        else:
            act0 = agent_p0(obs0)
            act1 = agent_p1(obs1)
            
        for p, act, obs_p in ((0, act0, obs0), (1, act1, obs1)):
            if isinstance(act, dict):
                for ord_item in act.get("market", []):
                    if len(ord_item) >= 3 and ord_item[0] == "SELL":
                        item, qty = ord_item[1], ord_item[2]
                        price = obs_p.market.prices.get(item, 0)
                        r = qty * price * 0.95
                        if item == "STRAWBERRY":
                            straw_rev[p] += r
                        else:
                            other_rev[p] += r
                            
        env.step([act0, act1])
        
    final_obs = env.state[0].observation
    res = {}
    for p in (0, 1):
        f = final_obs.farms[p]
        res[p] = {
            "money": f.money,
            "straw_rev": straw_rev[p],
            "other_rev": other_rev[p],
            "opp_straw_d11": opp_straw_d11[p]
        }
    return res

print("=" * 135)
print("PHASE-12 THREE-WAY SCIENTIFIC EVALUATION: RC2 CONTROL vs RC3-H6 vs RC4 FORECAST-CONFIRM (20 MATCHES)")
print("=" * 135)

results = {
    "RC2": {"scores": [], "straw_rev": [], "other_rev": [], "opp_straw": []},
    "RC3": {"scores": [], "straw_rev": [], "other_rev": [], "opp_straw": []},
    "RC4": {"scores": [], "straw_rev": [], "other_rev": [], "opp_straw": []}
}

# --- PART A: 5 High-Elo Replay Benchmarks (Seat 0 & Seat 1) ---
print("\n>>> PART A: High-Elo Replay Benchmarks (Seat 0 & Seat 1)")
print(f"{'OPPONENT':<24} | {'SEAT':<4} | {'OPP STRAW':>9} | {'RC2 SCORE':>11} | {'RC3 SCORE':>11} | {'RC4 SCORE':>11} | {'Diff(RC4-RC2)':>14} | {'Diff(RC4-RC3)':>14}")
print("-" * 135)

for r_name, opp_label in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    with open(path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions_s1 = [frame[1].get("action") for frame in steps[1:]]
    opp_actions_s0 = [frame[0].get("action") for frame in steps[1:]]
    
    # Seat 0
    tape_s1 = {s: (None, opp_actions_s1[s]) for s in range(len(opp_actions_s1))}
    r_rc2_0 = run_single_game(rc2_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    r_rc3_0 = run_single_game(rc3_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    r_rc4_0 = run_single_game(rc4_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    
    # Seat 1
    tape_s0 = {s: (opp_actions_s0[s], None) for s in range(len(opp_actions_s0))}
    r_rc2_1 = run_single_game(None, rc2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_rc3_1 = run_single_game(None, rc3_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_rc4_1 = run_single_game(None, rc4_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    
    for r in (r_rc2_0, r_rc2_1):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev"].append(r["straw_rev"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (r_rc3_0, r_rc3_1):
        results["RC3"]["scores"].append(r["money"])
        results["RC3"]["straw_rev"].append(r["straw_rev"])
        results["RC3"]["other_rev"].append(r["other_rev"])
        results["RC3"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (r_rc4_0, r_rc4_1):
        results["RC4"]["scores"].append(r["money"])
        results["RC4"]["straw_rev"].append(r["straw_rev"])
        results["RC4"]["other_rev"].append(r["other_rev"])
        results["RC4"]["opp_straw"].append(r["opp_straw_d11"])
        
    d2_0 = r_rc4_0['money'] - r_rc2_0['money']
    d3_0 = r_rc4_0['money'] - r_rc3_0['money']
    print(f"{opp_label:<24} | S0   | {r_rc4_0['opp_straw_d11']:>9} | ${r_rc2_0['money']:>10,.0f} | ${r_rc3_0['money']:>10,.0f} | ${r_rc4_0['money']:>10,.0f} | ${d2_0:>+13,.0f} | ${d3_0:>+13,.0f}")
    
    d2_1 = r_rc4_1['money'] - r_rc2_1['money']
    d3_1 = r_rc4_1['money'] - r_rc3_1['money']
    print(f"{opp_label:<24} | S1   | {r_rc4_1['opp_straw_d11']:>9} | ${r_rc2_1['money']:>10,.0f} | ${r_rc3_1['money']:>10,.0f} | ${r_rc4_1['money']:>10,.0f} | ${d2_1:>+13,.0f} | ${d3_1:>+13,.0f}")
    sys.stdout.flush()

# --- PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups vs RC2) ---
print("\n>>> PART B: 5 Live Low-Floor Seeds (Paired Seat-Swapped Matchups)")
print(f"{'MATCH / SEED':<24} | {'SEAT':<4} | {'OPP STRAW':>9} | {'RC2 SCORE':>11} | {'RC3 SCORE':>11} | {'RC4 SCORE':>11} | {'Diff(RC4-RC2)':>14} | {'Diff(RC4-RC3)':>14}")
print("-" * 135)

for seed, label in low_seeds:
    # Matchup 1: Candidate at Seat 0, RC2 at Seat 1
    m1_rc3 = run_single_game(rc3_mod.agent, rc2_mod.agent, seed)
    m1_rc4 = run_single_game(rc4_mod.agent, rc2_mod.agent, seed)
    rc2_s1 = m1_rc3[1] # baseline RC2 score in Seat 1
    rc3_s0 = m1_rc3[0]
    rc4_s0 = m1_rc4[0]
    
    # Matchup 2: RC2 at Seat 0, Candidate at Seat 1
    m2_rc3 = run_single_game(rc2_mod.agent, rc3_mod.agent, seed)
    m2_rc4 = run_single_game(rc2_mod.agent, rc4_mod.agent, seed)
    rc2_s0 = m2_rc3[0] # baseline RC2 score in Seat 0
    rc3_s1 = m2_rc3[1]
    rc4_s1 = m2_rc4[1]
    
    for r in (rc2_s0, rc2_s1):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev"].append(r["straw_rev"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (rc3_s0, rc3_s1):
        results["RC3"]["scores"].append(r["money"])
        results["RC3"]["straw_rev"].append(r["straw_rev"])
        results["RC3"]["other_rev"].append(r["other_rev"])
        results["RC3"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (rc4_s0, rc4_s1):
        results["RC4"]["scores"].append(r["money"])
        results["RC4"]["straw_rev"].append(r["straw_rev"])
        results["RC4"]["other_rev"].append(r["other_rev"])
        results["RC4"]["opp_straw"].append(r["opp_straw_d11"])
        
    d2_m1 = rc4_s0['money'] - rc2_s1['money']
    d3_m1 = rc4_s0['money'] - rc3_s0['money']
    print(f"{label:<24} | S0   | {rc4_s0['opp_straw_d11']:>9} | ${rc2_s1['money']:>10,.0f} | ${rc3_s0['money']:>10,.0f} | ${rc4_s0['money']:>10,.0f} | ${d2_m1:>+13,.0f} | ${d3_m1:>+13,.0f}")
    
    d2_m2 = rc4_s1['money'] - rc2_s0['money']
    d3_m2 = rc4_s1['money'] - rc3_s1['money']
    print(f"{label:<24} | S1   | {rc4_s1['opp_straw_d11']:>9} | ${rc2_s0['money']:>10,.0f} | ${rc3_s1['money']:>10,.0f} | ${rc4_s1['money']:>10,.0f} | ${d2_m2:>+13,.0f} | ${d3_m2:>+13,.0f}")
    sys.stdout.flush()

print("=" * 135)

all_rc2 = results["RC2"]["scores"]
all_rc3 = results["RC3"]["scores"]
all_rc4 = results["RC4"]["scores"]

mean_rc2, mean_rc3, mean_rc4 = sum(all_rc2)/len(all_rc2), sum(all_rc3)/len(all_rc3), sum(all_rc4)/len(all_rc4)
floor_rc2, floor_rc3, floor_rc4 = min(all_rc2), min(all_rc3), min(all_rc4)
ceil_rc2, ceil_rc3, ceil_rc4 = max(all_rc2), max(all_rc3), max(all_rc4)

print(f"{'Mean Score':<28} | {'-':>9} | ${mean_rc2:>10,.0f} | ${mean_rc3:>10,.0f} | ${mean_rc4:>10,.0f} | ${mean_rc4 - mean_rc2:>+13,.0f} | ${mean_rc4 - mean_rc3:>+13,.0f}")
print(f"{'Floor Score (Minimum)':<28} | {'-':>9} | ${floor_rc2:>10,.0f} | ${floor_rc3:>10,.0f} | ${floor_rc4:>10,.0f} | ${floor_rc4 - floor_rc2:>+13,.0f} | ${floor_rc4 - floor_rc3:>+13,.0f}")
print(f"{'Ceiling Score (Maximum)':<28} | {'-':>9} | ${ceil_rc2:>10,.0f} | ${ceil_rc3:>10,.0f} | ${ceil_rc4:>10,.0f} | ${ceil_rc4 - ceil_rc2:>+13,.0f} | ${ceil_rc4 - ceil_rc3:>+13,.0f}")

wins_v_rc2 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] > all_rc2[i])
ties_v_rc2 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] == all_rc2[i])
losses_v_rc2 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] < all_rc2[i])

wins_v_rc3 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] > all_rc3[i])
ties_v_rc3 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] == all_rc3[i])
losses_v_rc3 = sum(1 for i in range(len(all_rc4)) if all_rc4[i] < all_rc3[i])

print(f"Record vs RC2 Control: Wins: {wins_v_rc2} | Losses: {losses_v_rc2} | Ties: {ties_v_rc2} (Tied or Won: {wins_v_rc2 + ties_v_rc2}/20)")
print(f"Record vs RC3 Baseline: Wins: {wins_v_rc3} | Losses: {losses_v_rc3} | Ties: {ties_v_rc3} (Tied or Won: {wins_v_rc3 + ties_v_rc3}/20)")
print("=" * 135)

with open("reports/RC4_THREE_WAY_PAIRED_AUDIT.json", "w") as f:
    json.dump(results, f, indent=2)
print("Complete audit saved to reports/RC4_THREE_WAY_PAIRED_AUDIT.json")
