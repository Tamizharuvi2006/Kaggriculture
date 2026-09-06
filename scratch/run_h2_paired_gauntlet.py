import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json, time, importlib
import kaggle_environments

# Import agents
import submission_rc2_terminal_horizon as rc2_mod
import submission_h2_order_priority as h2_mod

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
    
    # Mechanism tracking
    hist = {
        0: {"cash_by_day": {}, "ne_unlock_day": None, "milk_rev": 0, "straw_rev": 0, "wool_rev": 0},
        1: {"cash_by_day": {}, "ne_unlock_day": None, "milk_rev": 0, "straw_rev": 0, "wool_rev": 0}
    }
    
    prev_day = -1
    for step in range(max_steps):
        if env.done: break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        day = obs0.day
        hour = obs0.hour
        
        # Track start of day cash & assets
        if day != prev_day:
            prev_day = day
            for p in (0, 1):
                f = obs0.farms[p]
                hist[p]["cash_by_day"][day] = f.money
                if "NE" in f.unlocked_quadrants and hist[p]["ne_unlock_day"] is None:
                    hist[p]["ne_unlock_day"] = day
                    
        # Get actions
        act0 = agent_p0(obs0) if agent_p0 else opp_tape[step][0]
        act1 = agent_p1(obs1) if agent_p1 else opp_tape[step][1]
        
        env.step([act0, act1])
        
    # Check final state
    final_obs = env.state[0].observation
    res = {}
    for p in (0, 1):
        f = final_obs.farms[p]
        priv = env.state[p].observation.private
        shed = priv.get("shed", {})
        shed_total = sum(shed.values())
        
        c_by_d = hist[p]["cash_by_day"]
        min_c = min(c_by_d.values()) if c_by_d else 0
        
        res[p] = {
            "money": f.money,
            "min_cash": min_c,
            "ne_day": hist[p]["ne_unlock_day"],
            "shed_total": shed_total,
        }
    return res

print("=" * 115)
print("PHASE-11 SCIENTIFIC EVALUATION: RC2 CONTROL vs H2 ORDER PRIORITY (PAIRED SEAT-SWAPPED)")
print("=" * 115)

results = {
    "RC2": {"scores": [], "min_cash": [], "ne_days": []},
    "H2":  {"scores": [], "min_cash": [], "ne_days": []}
}

# --- PART A: 5 High-Elo Replay Benchmarks (Seat 0 and Seat 1) ---
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
    r_h2_0 = run_single_game(h2_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    
    # 2. Seat 1: Replay Opponent at Seat 0, Agent at Seat 1
    tape_s0 = {s: (opp_actions_s0[s], None) for s in range(len(opp_actions_s0))}
    r_rc2_1 = run_single_game(None, rc2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_h2_1 = run_single_game(None, h2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    
    for r, tag in [(r_rc2_0, "RC2"), (r_rc2_1, "RC2")]:
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["min_cash"].append(r["min_cash"])
        results["RC2"]["ne_days"].append(r["ne_day"])
        
    for r, tag in [(r_h2_0, "H2"), (r_h2_1, "H2")]:
        results["H2"]["scores"].append(r["money"])
        results["H2"]["min_cash"].append(r["min_cash"])
        results["H2"]["ne_days"].append(r["ne_day"])
        
    print(f"  {opp_label:<26} | S0 RC2: ${r_rc2_0['money']:>7,.0f} | H2: ${r_h2_0['money']:>7,.0f} | Diff: ${r_h2_0['money']-r_rc2_0['money']:>+6,.0f}")
    print(f"  {'':<26} | S1 RC2: ${r_rc2_1['money']:>7,.0f} | H2: ${r_h2_1['money']:>7,.0f} | Diff: ${r_h2_1['money']-r_rc2_1['money']:>+6,.0f}")
    sys.stdout.flush()

# --- PART B: 5 Live Low-Floor Seeds (Direct Head-to-Head & Seat-Swapped) ---
print("\n>>> PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups)")
for seed, label in low_seeds:
    # Match 1: Seat 0 = H2, Seat 1 = RC2
    m1 = run_single_game(h2_mod.agent, rc2_mod.agent, seed)
    h2_m1, rc2_m1 = m1[0], m1[1]
    
    # Match 2: Seat 0 = RC2, Seat 1 = H2
    m2 = run_single_game(rc2_mod.agent, h2_mod.agent, seed)
    rc2_m2, h2_m2 = m2[0], m2[1]
    
    for r in (rc2_m1, rc2_m2):
        results["RC2"]["scores"].append(r["money"])
        results["RC2"]["min_cash"].append(r["min_cash"])
        results["RC2"]["ne_days"].append(r["ne_day"])
        
    for r in (h2_m1, h2_m2):
        results["H2"]["scores"].append(r["money"])
        results["H2"]["min_cash"].append(r["min_cash"])
        results["H2"]["ne_days"].append(r["ne_day"])
        
    print(f"  {label:<30} | M1(H2 S0 vs RC2 S1): H2: ${h2_m1['money']:>7,.0f} vs RC2: ${rc2_m1['money']:>7,.0f} (Diff: ${h2_m1['money']-rc2_m1['money']:>+6,.0f})")
    print(f"  {'':<30} | M2(RC2 S0 vs H2 S1): H2: ${h2_m2['money']:>7,.0f} vs RC2: ${rc2_m2['money']:>7,.0f} (Diff: ${h2_m2['money']-rc2_m2['money']:>+6,.0f})")
    sys.stdout.flush()

# --- SUMMARY STATISTICS ---
print("\n" + "=" * 115)
print(f"{'METRIC':<25} | {'RC2 CONTROL':>15} | {'H2 CANDIDATE':>15} | {'DELTA (H2 - RC2)':>18}")
print("-" * 115)

def get_stats(arr):
    s = sorted(arr)
    mean = sum(s) / len(s)
    med = (s[len(s)//2] + s[(len(s)-1)//2]) / 2
    return mean, med, s[0], s[-1]

rc2_s = results["RC2"]["scores"]
h2_s  = results["H2"]["scores"]
rc2_mean, rc2_med, rc2_min, rc2_max = get_stats(rc2_s)
h2_mean,  h2_med,  h2_min,  h2_max  = get_stats(h2_s)

print(f"{'Mean Score':<25} | ${rc2_mean:>14,.0f} | ${h2_mean:>14,.0f} | ${h2_mean - rc2_mean:>+17,.0f}")
print(f"{'Median Score':<25} | ${rc2_med:>14,.0f} | ${h2_med:>14,.0f} | ${h2_med - rc2_med:>+17,.0f}")
print(f"{'Minimum Score (Floor)':<25} | ${rc2_min:>14,.0f} | ${h2_min:>14,.0f} | ${h2_min - rc2_min:>+17,.0f}")
print(f"{'Maximum Score (Ceiling)':<25} | ${rc2_max:>14,.0f} | ${h2_max:>14,.0f} | ${h2_max - rc2_max:>+17,.0f}")

# Head-to-Head Win Rate in Part B
h2_wins = 0
rc2_wins = 0
ties = 0
for i in range(len(low_seeds)):
    # m1
    s_h2_m1 = h2_s[10 + 2*i]
    s_rc2_m1 = rc2_s[10 + 2*i]
    if s_h2_m1 > s_rc2_m1: h2_wins += 1
    elif s_h2_m1 < s_rc2_m1: rc2_wins += 1
    else: ties += 1
    # m2
    s_h2_m2 = h2_s[10 + 2*i + 1]
    s_rc2_m2 = rc2_s[10 + 2*i + 1]
    if s_h2_m2 > s_rc2_m2: h2_wins += 1
    elif s_h2_m2 < s_rc2_m2: rc2_wins += 1
    else: ties += 1

print("-" * 115)
print(f"Head-to-Head Record (Part B Low Seeds): H2 Wins: {h2_wins} | RC2 Wins: {rc2_wins} | Ties: {ties}")
print("=" * 115)

# Save audit report
with open("reports/H2_ORDER_PRIORITY_PAIRED_AUDIT.json", "w") as f:
    json.dump({
        "rc2_scores": rc2_s,
        "h2_scores": h2_s,
        "rc2_summary": {"mean": rc2_mean, "median": rc2_med, "min": rc2_min, "max": rc2_max},
        "h2_summary": {"mean": h2_mean, "median": h2_med, "min": h2_min, "max": h2_max},
        "head_to_head": {"h2_wins": h2_wins, "rc2_wins": rc2_wins, "ties": ties}
    }, f, indent=2)
print("\nComplete audit saved to reports/H2_ORDER_PRIORITY_PAIRED_AUDIT.json")
