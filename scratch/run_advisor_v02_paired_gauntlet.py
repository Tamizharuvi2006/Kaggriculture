import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json, time, importlib
import kaggle_environments

# Import agents
import submission_rc2_terminal_horizon as rc2_mod
import submission_rc2_market_advisor_v02 as adv_mod

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
    
    # Detailed trigger audit tracking
    triggers_log = []
    
    prev_mkt_inv = {}
    
    for step in range(max_steps):
        if env.done: break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        
        # Monitor trigger events for the active agents
        for p, obs in ((0, obs0), (1, obs1)):
            priv = env.state[p].observation.private
            shed = priv.get("shed", {})
            mkt = obs.market
            prices = mkt.prices
            inv = mkt.inventory
            
            p_milk = float(prices.get("MILK", 0) or 0)
            cur_inv = int(inv.get("MILK", 10000))
            last_inv = int(prev_mkt_inv.get(p, {}).get("MILK", 10000))
            di_milk = cur_inv - last_inv
            milk_qty = int(shed.get("MILK", 0))
            
            if p_milk >= 180.0 and di_milk > 0 and milk_qty > 0:
                triggers_log.append({
                    "step": step,
                    "player": p,
                    "cash": obs.farms[p].money,
                    "p_milk": p_milk,
                    "milk_qty": milk_qty,
                    "slot_chosen": 0 if obs.farms[p].money >= 600 else 1
                })
                
            if p not in prev_mkt_inv: prev_mkt_inv[p] = {}
            prev_mkt_inv[p] = dict(inv)
                
        act0 = agent_p0(obs0) if agent_p0 else opp_tape[step][0]
        act1 = agent_p1(obs1) if agent_p1 else opp_tape[step][1]
        
        env.step([act0, act1])
        
    final_obs = env.state[0].observation
    res = {}
    for p in (0, 1):
        f = final_obs.farms[p]
        res[p] = {
            "money": f.money,
            "triggers": [t for t in triggers_log if t["player"] == p]
        }
    return res

print("=" * 115)
print("PHASE-11 SCIENTIFIC EVALUATION: RC2 CONTROL vs SURGICAL ADVISOR v0.2 (PAIRED SEAT-SWAPPED)")
print("=" * 115)

results = {
    "RC2": {"scores": []},
    "ADV": {"scores": [], "triggers": []}
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
    r_adv_0 = run_single_game(adv_mod.agent, None, seed, opp_tape=tape_s1, max_steps=len(steps))[0]
    
    # 2. Seat 1: Replay Opponent at Seat 0, Agent at Seat 1
    tape_s0 = {s: (opp_actions_s0[s], None) for s in range(len(opp_actions_s0))}
    r_rc2_1 = run_single_game(None, rc2_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    r_adv_1 = run_single_game(None, adv_mod.agent, seed, opp_tape=tape_s0, max_steps=len(steps))[1]
    
    results["RC2"]["scores"].extend([r_rc2_0["money"], r_rc2_1["money"]])
    results["ADV"]["scores"].extend([r_adv_0["money"], r_adv_1["money"]])
    results["ADV"]["triggers"].extend([len(r_adv_0["triggers"]), len(r_adv_1["triggers"])])
    
    print(f"  {opp_label:<26} | S0 RC2: ${r_rc2_0['money']:>7,.0f} | ADV: ${r_adv_0['money']:>7,.0f} | Diff: ${r_adv_0['money']-r_rc2_0['money']:>+6,.0f} (Triggers: {len(r_adv_0['triggers'])})")
    print(f"  {'':<26} | S1 RC2: ${r_rc2_1['money']:>7,.0f} | ADV: ${r_adv_1['money']:>7,.0f} | Diff: ${r_adv_1['money']-r_rc2_1['money']:>+6,.0f} (Triggers: {len(r_adv_1['triggers'])})")
    sys.stdout.flush()

# --- PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups) ---
print("\n>>> PART B: 5 Live Low-Floor Seeds (Head-to-Head Paired Matchups)")
for seed, label in low_seeds:
    # Match 1: Seat 0 = ADV, Seat 1 = RC2
    m1 = run_single_game(adv_mod.agent, rc2_mod.agent, seed)
    adv_m1, rc2_m1 = m1[0], m1[1]
    
    # Match 2: Seat 0 = RC2, Seat 1 = ADV
    m2 = run_single_game(rc2_mod.agent, adv_mod.agent, seed)
    rc2_m2, adv_m2 = m2[0], m2[1]
    
    results["RC2"]["scores"].extend([rc2_m1["money"], rc2_m2["money"]])
    results["ADV"]["scores"].extend([adv_m1["money"], adv_m2["money"]])
    results["ADV"]["triggers"].extend([len(adv_m1["triggers"]), len(adv_m2["triggers"])])
    
    print(f"  {label:<30} | M1(ADV S0 vs RC2 S1): ADV: ${adv_m1['money']:>7,.0f} vs RC2: ${rc2_m1['money']:>7,.0f} (Diff: ${adv_m1['money']-rc2_m1['money']:>+6,.0f})")
    print(f"  {'':<30} | M2(RC2 S0 vs ADV S1): ADV: ${adv_m2['money']:>7,.0f} vs RC2: ${rc2_m2['money']:>7,.0f} (Diff: ${adv_m2['money']-rc2_m2['money']:>+6,.0f})")
    sys.stdout.flush()

# --- SUMMARY STATISTICS ---
print("\n" + "=" * 115)
print(f"{'METRIC':<25} | {'RC2 CONTROL':>15} | {'ADV CANDIDATE':>15} | {'DELTA (ADV - RC2)':>18}")
print("-" * 115)

def get_stats(arr):
    s = sorted(arr)
    mean = sum(s) / len(s)
    med = (s[len(s)//2] + s[(len(s)-1)//2]) / 2
    return mean, med, s[0], s[-1]

rc2_s = results["RC2"]["scores"]
adv_s = results["ADV"]["scores"]
rc2_mean, rc2_med, rc2_min, rc2_max = get_stats(rc2_s)
adv_mean, adv_med, adv_min, adv_max = get_stats(adv_s)

print(f"{'Mean Score':<25} | ${rc2_mean:>14,.0f} | ${adv_mean:>14,.0f} | ${adv_mean - rc2_mean:>+17,.0f}")
print(f"{'Median Score':<25} | ${rc2_med:>14,.0f} | ${adv_med:>14,.0f} | ${adv_med - rc2_med:>+17,.0f}")
print(f"{'Minimum Score (Floor)':<25} | ${rc2_min:>14,.0f} | ${adv_min:>14,.0f} | ${adv_min - rc2_min:>+17,.0f}")
print(f"{'Maximum Score (Ceiling)':<25} | ${rc2_max:>14,.0f} | ${adv_max:>14,.0f} | ${adv_max - rc2_max:>+17,.0f}")

# Head-to-Head Win Rate in Part B
adv_wins = 0
rc2_wins = 0
ties = 0
for i in range(len(low_seeds)):
    # m1
    s_adv_m1 = adv_s[10 + 2*i]
    s_rc2_m1 = rc2_s[10 + 2*i]
    if s_adv_m1 > s_rc2_m1: adv_wins += 1
    elif s_adv_m1 < s_rc2_m1: rc2_wins += 1
    else: ties += 1
    # m2
    s_adv_m2 = adv_s[10 + 2*i + 1]
    s_rc2_m2 = rc2_s[10 + 2*i + 1]
    if s_adv_m2 > s_rc2_m2: adv_wins += 1
    elif s_adv_m2 < s_rc2_m2: rc2_wins += 1
    else: ties += 1

print("-" * 115)
print(f"Head-to-Head Record (Part B Low Seeds): ADV Wins: {adv_wins} | RC2 Wins: {rc2_wins} | Ties: {ties}")
print(f"Average Advisor Reorder Triggers per Match: {sum(results['ADV']['triggers'])/len(results['ADV']['triggers']):.1f} events")
print("=" * 115)

# Save audit report
with open("reports/ADVISOR_V02_PAIRED_AUDIT.json", "w") as f:
    json.dump({
        "rc2_scores": rc2_s,
        "adv_scores": adv_s,
        "rc2_summary": {"mean": rc2_mean, "median": rc2_med, "min": rc2_min, "max": rc2_max},
        "adv_summary": {"mean": adv_mean, "median": adv_med, "min": adv_min, "max": adv_max},
        "head_to_head": {"adv_wins": adv_wins, "rc2_wins": rc2_wins, "ties": ties}
    }, f, indent=2)
print("\nComplete audit saved to reports/ADVISOR_V02_PAIRED_AUDIT.json")
