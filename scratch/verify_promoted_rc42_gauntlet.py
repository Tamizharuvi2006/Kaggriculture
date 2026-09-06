import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
from concurrent.futures import ProcessPoolExecutor
import kaggle_environments

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

def run_agent_match(args):
    agent_mod_name, label, r_path, s_val, seat = args
    if agent_mod_name == "rc41":
        import submission_rc4_1_clean as bot_mod
    else:
        import submission_rc4_2_hybrid as bot_mod
        
    if r_path:
        p = os.path.join(r"reports/live_match_telemetry", r_path)
        with open(p) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = s_val
        opp_actions = None
        max_steps = 720
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        act_bot = bot_mod.agent(obs)
        if r_path:
            opp_act = opp_actions[step]
        else:
            opp_act = bot_mod.agent(env.state[1 - seat].observation)
        acts = [opp_act, act_bot] if seat == 1 else [act_bot, opp_act]
        env.step(acts)
        
    score = env.state[seat].observation.farms[seat].money
    confirm_day = getattr(bot_mod, "_FLOOD_CONFIRMED_DAY", None) if getattr(bot_mod, "_FLOOD_CONFIRMED", False) else None
    return score, confirm_day

def run_paired_verification(match_args):
    label, r_path, s_val, seat = match_args
    s_rc41, c_rc41 = run_agent_match(("rc41", label, r_path, s_val, seat))
    s_rc42, c_rc42 = run_agent_match(("rc42", label, r_path, s_val, seat))
    return label, seat, s_rc41, s_rc42, c_rc41, c_rc42

if __name__ == "__main__":
    match_tasks = []
    for r_name, opp_label in replays:
        for seat in (0, 1):
            match_tasks.append((opp_label, r_name, None, seat))
    for s_val, label in low_seeds:
        for seat in (0, 1):
            match_tasks.append((label, None, s_val, seat))
            
    print("=" * 125)
    print("FORMAL 20-MATCH VERIFICATION: RC4.1-Clean vs RC4.2-Hybrid (STANDALONE MODULES)")
    print("=" * 125)
    print(f"{'MATCH / OPPONENT':<28} | {'SEAT':<4} | {'RC4.1 SCORE':>12} | {'RC4.2 SCORE':>12} | {'DELTA':>10} | {'RC4.2 CONF':>11}")
    print("-" * 125)
    sys.stdout.flush()
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_paired_verification, match_tasks))
        
    diffs = []
    scores_rc41 = []
    scores_rc42 = []
    
    for label, seat, s1, s2, c1, c2 in results:
        d = s2 - s1
        diffs.append(d)
        scores_rc41.append(s1)
        scores_rc42.append(s2)
        c_str = f"Day {c2}" if c2 else "NO"
        print(f"{label:<28} | S{seat}  | ${s1:>11,.0f} | ${s2:>11,.0f} | ${d:>+9,.0f} | {c_str:>11}")
        sys.stdout.flush()
        
    print("=" * 125)
    print(f"{'Mean Score':<28} | {'-':<4} | ${sum(scores_rc41)/len(scores_rc41):>11,.0f} | ${sum(scores_rc42)/len(scores_rc42):>11,.0f} | ${sum(diffs)/len(diffs):>+9,.0f}")
    print(f"{'Global Suite Minimum':<28} | {'-':<4} | ${min(scores_rc41):>11,.0f} | ${min(scores_rc42):>11,.0f} | ${min(scores_rc42) - min(scores_rc41):>+9,.0f}")
    print(f"{'Maximum Ceiling':<28} | {'-':<4} | ${max(scores_rc41):>11,.0f} | ${max(scores_rc42):>11,.0f} | ${max(scores_rc42) - max(scores_rc41):>+9,.0f}")
    wins = sum(1 for x in diffs if x > 0)
    ties = sum(1 for x in diffs if x == 0)
    losses = sum(1 for x in diffs if x < 0)
    print(f"RC4.2 Record vs RC4.1: Wins: {wins} | Losses: {losses} | Ties: {ties} (Tied or Won: {wins + ties}/20 = {(wins+ties)/20*100:.1f}%)")
    print("=" * 125)
