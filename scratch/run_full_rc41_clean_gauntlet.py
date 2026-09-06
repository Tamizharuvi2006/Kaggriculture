import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

# Import agents
import submission_rc2_terminal_horizon as rc2_mod
import submission_rc3_h6 as rc3_mod
import submission_rc4_1_clean as rc41_mod

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
    
    straw_rev_pre = {0: 0.0, 1: 0.0}
    straw_rev_post = {0: 0.0, 1: 0.0}
    other_rev = {0: 0.0, 1: 0.0}
    opp_straw_d11 = {0: 0, 1: 0}
    peak_inv = 0
    min_p_straw = 999.0
    
    confirm_day = None
    
    for step in range(max_steps):
        if env.done: break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        day = obs0.day
        hour = obs0.hour
        
        inv_straw = int(obs0.market.inventory.get("STRAWBERRY", 10000))
        p_straw = float(obs0.market.prices.get("STRAWBERRY", 120))
        if inv_straw > peak_inv: peak_inv = inv_straw
        if p_straw < min_p_straw: min_p_straw = p_straw
        
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
            
        # Check if RC4.1 confirmed
        if confirm_day is None and getattr(rc41_mod, "_FLOOD_CONFIRMED", False):
            confirm_day = getattr(rc41_mod, "_FLOOD_CONFIRMED_DAY", day)
            
        for p, act, obs_p in ((0, act0, obs0), (1, act1, obs1)):
            if isinstance(act, dict):
                for ord_item in act.get("market", []):
                    if len(ord_item) >= 3 and ord_item[0] == "SELL":
                        item, qty = ord_item[1], ord_item[2]
                        price = obs_p.market.prices.get(item, 0)
                        r = qty * price * 0.95
                        if item == "STRAWBERRY":
                            if confirm_day is None or day <= confirm_day:
                                straw_rev_pre[p] += r
                            else:
                                straw_rev_post[p] += r
                        else:
                            other_rev[p] += r
                            
        env.step([act0, act1])
        
    final_obs = env.state[0].observation
    res = {}
    for p in (0, 1):
        f = final_obs.farms[p]
        res[p] = {
            "money": f.money,
            "straw_rev_pre": straw_rev_pre[p],
            "straw_rev_post": straw_rev_post[p],
            "straw_rev_total": straw_rev_pre[p] + straw_rev_post[p],
            "other_rev": other_rev[p],
            "opp_straw_d11": opp_straw_d11[p],
            "confirm_day": confirm_day,
            "peak_inv": peak_inv,
            "min_p_straw": min_p_straw
        }
    return res

print("=" * 140)
print("PHASE-13 THREE-WAY SCIENTIFIC GAUNTLET: RC2 CONTROL vs RC3-H6 vs RC4.1-CLEAN (20 MATCHES)")
print("=" * 140)

results = {
    "RC2": {"scores": [], "straw_rev_pre": [], "straw_rev_post": [], "other_rev": [], "opp_straw": []},
    "RC3": {"scores": [], "straw_rev_pre": [], "straw_rev_post": [], "other_rev": [], "opp_straw": []},
    "RC41": {"scores": [], "straw_rev_pre": [], "straw_rev_post": [], "other_rev": [], "opp_straw": [], "confirm_day": []}
}

# --- PART A: 5 High-Elo Replay Benchmarks (Seat 0 & Seat 1) ---
print("\n>>> PART A: High-Elo Replay Benchmarks (Seat 0 & Seat 1)")
print(f"{'OPPONENT':<24} | {'SEAT':<4} | {'OPP STRAW':>9} | {'RC2 SCORE':>11} | {'RC3 SCORE':>11} | {'RC4.1 SCORE':>11} | {'Diff(RC4.1-RC2)':>15} | {'Diff(RC4.1-RC3)':>15} | {'CONFIRM':>7}")
print("-" * 140)

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
    r_rc41_0 = run_single_game(rc41_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    
    # Seat 1
    tape_s0 = {s: (opp_actions_s0[s], None) for s in range(len(opp_actions_s0))}
    r_rc2_1 = run_single_game(None, rc2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_rc3_1 = run_single_game(None, rc3_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_rc41_1 = run_single_game(None, rc41_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    
    for r in (r_rc2_0, r_rc2_1):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC2"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (r_rc3_0, r_rc3_1):
        results["RC3"]["scores"].append(r["money"])
        results["RC3"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC3"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC3"]["other_rev"].append(r["other_rev"])
        results["RC3"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (r_rc41_0, r_rc41_1):
        results["RC41"]["scores"].append(r["money"])
        results["RC41"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC41"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC41"]["other_rev"].append(r["other_rev"])
        results["RC41"]["opp_straw"].append(r["opp_straw_d11"])
        results["RC41"]["confirm_day"].append(r["confirm_day"])
        
    d2_0 = r_rc41_0['money'] - r_rc2_0['money']
    d3_0 = r_rc41_0['money'] - r_rc3_0['money']
    c_str_0 = f"D{r_rc41_0['confirm_day']}" if r_rc41_0['confirm_day'] else "NO"
    print(f"{opp_label:<24} | S0   | {r_rc41_0['opp_straw_d11']:>9} | ${r_rc2_0['money']:>10,.0f} | ${r_rc3_0['money']:>10,.0f} | ${r_rc41_0['money']:>10,.0f} | ${d2_0:>+14,.0f} | ${d3_0:>+14,.0f} | {c_str_0:>7}")
    
    d2_1 = r_rc41_1['money'] - r_rc2_1['money']
    d3_1 = r_rc41_1['money'] - r_rc3_1['money']
    c_str_1 = f"D{r_rc41_1['confirm_day']}" if r_rc41_1['confirm_day'] else "NO"
    print(f"{opp_label:<24} | S1   | {r_rc41_1['opp_straw_d11']:>9} | ${r_rc2_1['money']:>10,.0f} | ${r_rc3_1['money']:>10,.0f} | ${r_rc41_1['money']:>10,.0f} | ${d2_1:>+14,.0f} | ${d3_1:>+14,.0f} | {c_str_1:>7}")
    sys.stdout.flush()

# --- PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups vs RC2) ---
print("\n>>> PART B: 5 Live Low-Floor Seeds (Paired Seat-Swapped Matchups)")
print(f"{'MATCH / SEED':<24} | {'SEAT':<4} | {'OPP STRAW':>9} | {'RC2 SCORE':>11} | {'RC3 SCORE':>11} | {'RC4.1 SCORE':>11} | {'Diff(RC4.1-RC2)':>15} | {'Diff(RC4.1-RC3)':>15} | {'CONFIRM':>7}")
print("-" * 140)

for seed, label in low_seeds:
    m1_rc3 = run_single_game(rc3_mod.agent, rc2_mod.agent, seed)
    m1_rc41 = run_single_game(rc41_mod.agent, rc2_mod.agent, seed)
    rc2_s1 = m1_rc3[1]
    rc3_s0 = m1_rc3[0]
    rc41_s0 = m1_rc41[0]
    
    m2_rc3 = run_single_game(rc2_mod.agent, rc3_mod.agent, seed)
    m2_rc41 = run_single_game(rc2_mod.agent, rc41_mod.agent, seed)
    rc2_s0 = m2_rc3[0]
    rc3_s1 = m2_rc3[1]
    rc41_s1 = m2_rc41[1]
    
    for r in (rc2_s0, rc2_s1):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC2"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC2"]["other_rev"].append(r["other_rev"])
        results["RC2"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (rc3_s0, rc3_s1):
        results["RC3"]["scores"].append(r["money"])
        results["RC3"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC3"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC3"]["other_rev"].append(r["other_rev"])
        results["RC3"]["opp_straw"].append(r["opp_straw_d11"])
        
    for r in (rc41_s0, rc41_s1):
        results["RC41"]["scores"].append(r["money"])
        results["RC41"]["straw_rev_pre"].append(r["straw_rev_pre"])
        results["RC41"]["straw_rev_post"].append(r["straw_rev_post"])
        results["RC41"]["other_rev"].append(r["other_rev"])
        results["RC41"]["opp_straw"].append(r["opp_straw_d11"])
        results["RC41"]["confirm_day"].append(r["confirm_day"])
        
    d2_m1 = rc41_s0['money'] - rc2_s1['money']
    d3_m1 = rc41_s0['money'] - rc3_s0['money']
    c_str_m1 = f"D{rc41_s0['confirm_day']}" if rc41_s0['confirm_day'] else "NO"
    print(f"{label:<24} | S0   | {rc41_s0['opp_straw_d11']:>9} | ${rc2_s1['money']:>10,.0f} | ${rc3_s0['money']:>10,.0f} | ${rc41_s0['money']:>10,.0f} | ${d2_m1:>+14,.0f} | ${d3_m1:>+14,.0f} | {c_str_m1:>7}")
    
    d2_m2 = rc41_s1['money'] - rc2_s0['money']
    d3_m2 = rc41_s1['money'] - rc3_s1['money']
    c_str_m2 = f"D{rc41_s1['confirm_day']}" if rc41_s1['confirm_day'] else "NO"
    print(f"{label:<24} | S1   | {rc41_s1['opp_straw_d11']:>9} | ${rc2_s0['money']:>10,.0f} | ${rc3_s1['money']:>10,.0f} | ${rc41_s1['money']:>10,.0f} | ${d2_m2:>+14,.0f} | ${d3_m2:>+14,.0f} | {c_str_m2:>7}")
    sys.stdout.flush()

print("=" * 140)

all_rc2 = results["RC2"]["scores"]
all_rc3 = results["RC3"]["scores"]
all_rc41 = results["RC41"]["scores"]

mean_rc2, mean_rc3, mean_rc41 = sum(all_rc2)/len(all_rc2), sum(all_rc3)/len(all_rc3), sum(all_rc41)/len(all_rc41)
floor_rc2, floor_rc3, floor_rc41 = min(all_rc2), min(all_rc3), min(all_rc41)
ceil_rc2, ceil_rc3, ceil_rc41 = max(all_rc2), max(all_rc3), max(all_rc41)

print(f"{'Mean Score':<28} | {'-':>9} | ${mean_rc2:>10,.0f} | ${mean_rc3:>10,.0f} | ${mean_rc41:>10,.0f} | ${mean_rc41 - mean_rc2:>+14,.0f} | ${mean_rc41 - mean_rc3:>+14,.0f} | {'-':>7}")
print(f"{'Floor Score (Minimum)':<28} | {'-':>9} | ${floor_rc2:>10,.0f} | ${floor_rc3:>10,.0f} | ${floor_rc41:>10,.0f} | ${floor_rc41 - floor_rc2:>+14,.0f} | ${floor_rc41 - floor_rc3:>+14,.0f} | {'-':>7}")
print(f"{'Ceiling Score (Maximum)':<28} | {'-':>9} | ${ceil_rc2:>10,.0f} | ${ceil_rc3:>10,.0f} | ${ceil_rc41:>10,.0f} | ${ceil_rc41 - ceil_rc2:>+14,.0f} | ${ceil_rc41 - ceil_rc3:>+14,.0f} | {'-':>7}")

wins_v_rc2 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] > all_rc2[i])
ties_v_rc2 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] == all_rc2[i])
losses_v_rc2 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] < all_rc2[i])

wins_v_rc3 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] > all_rc3[i])
ties_v_rc3 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] == all_rc3[i])
losses_v_rc3 = sum(1 for i in range(len(all_rc41)) if all_rc41[i] < all_rc3[i])

print(f"Record vs RC2 Control: Wins: {wins_v_rc2} | Losses: {losses_v_rc2} | Ties: {ties_v_rc2} (Tied or Won: {wins_v_rc2 + ties_v_rc2}/20)")
print(f"Record vs RC3 Baseline: Wins: {wins_v_rc3} | Losses: {losses_v_rc3} | Ties: {ties_v_rc3} (Tied or Won: {wins_v_rc3 + ties_v_rc3}/20)")
print("=" * 140)

with open("reports/RC41_CLEAN_THREE_WAY_PAIRED_AUDIT.json", "w") as f:
    json.dump(results, f, indent=2)
print("Complete audit saved to reports/RC41_CLEAN_THREE_WAY_PAIRED_AUDIT.json")
