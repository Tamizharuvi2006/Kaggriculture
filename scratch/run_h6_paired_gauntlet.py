import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json, time
import kaggle_environments

# Import agents
import submission_rc2_terminal_horizon as rc2_mod
import submission_h6_adaptive_allocation as h6_mod

replays = [
    ("episode-104475527-replay.json", "RicardoLópez (1052 Elo)"),
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
        
        # Check opponent strawberries at Day 11 Hour 0
        if day == 11 and hour == 0:
            for p, obs in ((0, obs0), (1, obs1)):
                opp = obs.farms[1 - p]
                opp_straw_d11[p] = sum(1 for r in opp.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                
        act0 = agent_p0(obs0) if agent_p0 else opp_tape[step][0]
        act1 = agent_p1(obs1) if agent_p1 else opp_tape[step][1]
        
        # Track market sales
        for p, act in ((0, act0), (1, act1)):
            if not isinstance(act, dict): continue
            mkt = act.get("market", [])
            for ord_item in mkt:
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item = ord_item[1]
                    qty = ord_item[2]
                    price = obs0.market.prices.get(item, 0)
                    rev = qty * price * 0.95
                    if item == "STRAWBERRY":
                        straw_rev[p] += rev
                    else:
                        other_rev[p] += rev
                        
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

print("=" * 125)
print("PHASE-11 SCIENTIFIC EVALUATION: RC2 CONTROL vs H6 ADAPTIVE ALLOCATION (PAIRED SEAT-SWAPPED)")
print("=" * 125)

results = {
    "RC2": {"scores": [], "straw_rev": [], "other_rev": [], "opp_straw": []},
    "H6":  {"scores": [], "straw_rev": [], "other_rev": [], "opp_straw": []}
}

# --- PART A: 5 High-Elo Replay Benchmarks (Seat 0 & Seat 1) ---
print("\n>>> PART A: High-Elo Replay Benchmarks (Seat 0 & Seat 1)")
for r_name, opp_label in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    with open(path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions_s1 = [frame[1].get("action") for frame in steps[1:]]
    opp_actions_s0 = [frame[0].get("action") for frame in steps[1:]]
    
    # 1. Seat 0: Agent at Seat 0, Replay Opponent at Seat 1
    tape_s1 = {s: (None, opp_actions_s1[s]) for s in range(len(opp_actions_s1))}
    r_rc2_0 = run_single_game(rc2_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    r_h6_0  = run_single_game(h6_mod.agent,  None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    
    # 2. Seat 1: Replay Opponent at Seat 0, Agent at Seat 1
    tape_s0 = {s: (opp_actions_s0[s], None) for s in range(len(opp_actions_s0))}
    r_rc2_1 = run_single_game(None, rc2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_h6_1  = run_single_game(None, h6_mod.agent,  seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    
    for r in (r_rc2_0, r_rc2_1):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev"].append(r["straw_rev"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (r_h6_0, r_h6_1):
        results["H6"]["scores"].append(r["money"])
        results["H6"]["straw_rev"].append(r["straw_rev"])
        results["H6"]["other_rev"].append(r["other_rev"])
        results["H6"]["opp_straw"].append(r["opp_straw_d11"])
        
    print(f"  {opp_label:<26} | S0 RC2: ${r_rc2_0['money']:>7,.0f} | H6: ${r_h6_0['money']:>7,.0f} | Diff: ${r_h6_0['money']-r_rc2_0['money']:>+7,.0f} (Opp Straw: {r_rc2_0['opp_straw_d11']})")
    print(f"  {'':<26} | S1 RC2: ${r_rc2_1['money']:>7,.0f} | H6: ${r_h6_1['money']:>7,.0f} | Diff: ${r_h6_1['money']-r_rc2_1['money']:>+7,.0f} (Opp Straw: {r_rc2_1['opp_straw_d11']})")
    sys.stdout.flush()

# --- PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups) ---
print("\n>>> PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups)")
for seed, label in low_seeds:
    # Match 1: Seat 0 = H6, Seat 1 = RC2
    m1 = run_single_game(h6_mod.agent, rc2_mod.agent, seed)
    h6_m1, rc2_m1 = m1[0], m1[1]
    
    # Match 2: Seat 0 = RC2, Seat 1 = H6
    m2 = run_single_game(rc2_mod.agent, h6_mod.agent, seed)
    rc2_m2, h6_m2 = m2[0], m2[1]
    
    for r in (rc2_m1, rc2_m2):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev"].append(r["straw_rev"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (h6_m1, h6_m2):
        results["H6"]["scores"].append(r["money"])
        results["H6"]["straw_rev"].append(r["straw_rev"])
        results["H6"]["other_rev"].append(r["other_rev"])
        results["H6"]["opp_straw"].append(r["opp_straw_d11"])
        
    print(f"  {label:<30} | M1(H6 S0 vs RC2 S1): H6: ${h6_m1['money']:>7,.0f} vs RC2: ${rc2_m1['money']:>7,.0f} (Diff: ${h6_m1['money']-rc2_m1['money']:>+7,.0f})")
    print(f"  {'':<30} | M2(RC2 S0 vs H6 S1): H6: ${h6_m2['money']:>7,.0f} vs RC2: ${rc2_m2['money']:>7,.0f} (Diff: ${h6_m2['money']-rc2_m2['money']:>+7,.0f})")
    sys.stdout.flush()

# --- SUMMARY STATISTICS ---
print("\n" + "=" * 125)
print(f"{'METRIC':<30} | {'RC2 CONTROL':>15} | {'H6 CANDIDATE':>15} | {'DELTA (H6 - RC2)':>18}")
print("-" * 125)

def get_stats(arr):
    s = sorted(arr)
    mean = sum(s) / len(s)
    med = (s[len(s)//2] + s[(len(s)-1)//2]) / 2
    return mean, med, s[0], s[-1]

rc2_s = results["RC2"]["scores"]
h6_s  = results["H6"]["scores"]
rc2_mean, rc2_med, rc2_min, rc2_max = get_stats(rc2_s)
h6_mean,  h6_med,  h6_min,  h6_max  = get_stats(h6_s)

print(f"{'Mean Score':<30} | ${rc2_mean:>14,.0f} | ${h6_mean:>14,.0f} | ${h6_mean - rc2_mean:>+17,.0f}")
print(f"{'Median Score':<30} | ${rc2_med:>14,.0f} | ${h6_med:>14,.0f} | ${h6_med - rc2_med:>+17,.0f}")
print(f"{'Minimum Score (Floor)':<30} | ${rc2_min:>14,.0f} | ${h6_min:>14,.0f} | ${h6_min - rc2_min:>+17,.0f}")
print(f"{'Maximum Score (Ceiling)':<30} | ${rc2_max:>14,.0f} | ${h6_max:>14,.0f} | ${h6_max - rc2_max:>+17,.0f}")

# Revenue breakdowns
tot_rc2_straw = sum(results["RC2"]["straw_rev"]) / len(rc2_s)
tot_h6_straw  = sum(results["H6"]["straw_rev"]) / len(h6_s)
tot_rc2_other = sum(results["RC2"]["other_rev"]) / len(rc2_s)
tot_h6_other  = sum(results["H6"]["other_rev"]) / len(h6_s)

print("-" * 125)
print(f"{'Avg Strawberry Revenue / Match':<30} | ${tot_rc2_straw:>14,.0f} | ${tot_h6_straw:>14,.0f} | ${tot_h6_straw - tot_rc2_straw:>+17,.0f}")
print(f"{'Avg Replacement Revenue / Match':<30} | ${tot_rc2_other:>14,.0f} | ${tot_h6_other:>14,.0f} | ${tot_h6_other - tot_rc2_other:>+17,.0f}")

# Head-to-Head Win Rate in Part B
h6_wins = 0
rc2_wins = 0
ties = 0
for i in range(len(low_seeds)):
    s_h6_m1  = h6_s[10 + 2*i]
    s_rc2_m1 = rc2_s[10 + 2*i]
    if s_h6_m1 > s_rc2_m1: h6_wins += 1
    elif s_h6_m1 < s_rc2_m1: rc2_wins += 1
    else: ties += 1
    
    s_h6_m2  = h6_s[10 + 2*i + 1]
    s_rc2_m2 = rc2_s[10 + 2*i + 1]
    if s_h6_m2 > s_rc2_m2: h6_wins += 1
    elif s_h6_m2 < s_rc2_m2: rc2_wins += 1
    else: ties += 1

print("-" * 125)
print(f"Head-to-Head Record (Part B Low Seeds): H6 Wins: {h6_wins} | RC2 Wins: {rc2_wins} | Ties: {ties}")
print("=" * 125)

# Save audit report
with open("reports/H6_ADAPTIVE_ALLOCATION_PAIRED_AUDIT.json", "w") as f:
    json.dump({
        "rc2_scores": rc2_s,
        "h6_scores": h6_s,
        "rc2_summary": {"mean": rc2_mean, "median": rc2_med, "min": rc2_min, "max": rc2_max},
        "h6_summary": {"mean": h6_mean, "median": h6_med, "min": h6_min, "max": h6_max},
        "revenue_breakdown": {
            "avg_rc2_straw": tot_rc2_straw, "avg_h6_straw": tot_h6_straw,
            "avg_rc2_other": tot_rc2_other, "avg_h6_other": tot_h6_other
        },
        "head_to_head": {"h6_wins": h6_wins, "rc2_wins": rc2_wins, "ties": ties}
    }, f, indent=2)
print("\nComplete audit saved to reports/H6_ADAPTIVE_ALLOCATION_PAIRED_AUDIT.json")
