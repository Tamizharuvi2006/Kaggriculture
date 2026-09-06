import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
from concurrent.futures import ProcessPoolExecutor
import kaggle_environments

step5b_dir = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\ppo_submission_replays"
candidate_reps = []
for root, dirs, files in os.walk(step5b_dir):
    for f in files:
        if f.endswith("-replay.json"):
            candidate_reps.append(os.path.join(root, f))
            
candidate_reps.sort()
# Select 10 unseen replays across diverse match IDs
selected_reps = candidate_reps[:10]

def run_agent_match(args):
    agent_mod_name, r_path, seat = args
    if agent_mod_name == "rc41":
        import submission_rc4_1_clean as bot_mod
    else:
        import submission_rc4_2_hybrid as bot_mod
        
    with open(r_path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
    max_steps = len(steps) - 1
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        act_bot = bot_mod.agent(obs)
        opp_act = opp_actions[step]
        acts = [opp_act, act_bot] if seat == 1 else [act_bot, opp_act]
        env.step(acts)
        
    score = env.state[seat].observation.farms[seat].money
    confirm_day = getattr(bot_mod, "_FLOOD_CONFIRMED_DAY", None) if getattr(bot_mod, "_FLOOD_CONFIRMED", False) else None
    return score, confirm_day

def run_paired_verification(match_args):
    r_path, seat = match_args
    label = os.path.basename(r_path).replace("-replay.json", "")
    s_rc41, c_rc41 = run_agent_match(("rc41", r_path, seat))
    s_rc42, c_rc42 = run_agent_match(("rc42", r_path, seat))
    return label, seat, s_rc41, s_rc42, c_rc41, c_rc42

if __name__ == "__main__":
    match_tasks = []
    for p in selected_reps:
        for seat in (0, 1):
            match_tasks.append((p, seat))
            
    print("=" * 125)
    print("OUT-OF-SAMPLE 20-MATCH GAUNTLET: RC4.1-Clean vs RC4.2-Hybrid (10 UNSEEN PAIRED REPLAYS)")
    print("=" * 125)
    print(f"{'UNSEEN REPLAY':<28} | {'SEAT':<4} | {'RC4.1 SCORE':>12} | {'RC4.2 SCORE':>12} | {'DELTA':>10} | {'RC4.2 CONF':>11}")
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
