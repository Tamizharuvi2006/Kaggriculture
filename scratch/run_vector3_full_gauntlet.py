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

def run_single_sim(args):
    label, r_path, s_val, seat, portfolio_mode = args
    import submission_rc4_1_clean as rc41_mod
    
    if r_path:
        p = os.path.join(r"D:\kaggriculture", r_path)
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
    
    orig_crop_plan = rc41_mod._crop_plan
    
    def custom_crop_plan(day):
        plan = orig_crop_plan(day)
        if getattr(rc41_mod, "_FLOOD_CONFIRMED", False) and day >= 11:
            flex_plots = [pos for pos, c in plan.items() if c not in ("WHEAT", "STRAWBERRY")]
            if len(flex_plots) >= 2:
                if portfolio_mode == "2-carrots":
                    plan[flex_plots[0]] = "CARROT"
                    plan[flex_plots[1]] = "CARROT"
                elif portfolio_mode == "1-carrot-1-wheat":
                    plan[flex_plots[0]] = "CARROT"
                    plan[flex_plots[1]] = "WHEAT"
        return plan

    rc41_mod._crop_plan = custom_crop_plan
    
    confirm_day = None
    confirm_hour = None
    
    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        
        act_bot = rc41_mod.agent(obs)
        if r_path:
            opp_act = opp_actions[step]
        else:
            opp_act = rc41_mod.agent(env.state[1 - seat].observation)
        acts = [opp_act, act_bot] if seat == 1 else [act_bot, opp_act]
        
        if getattr(rc41_mod, "_FLOOD_CONFIRMED", False) and confirm_day is None:
            confirm_day = getattr(rc41_mod, "_FLOOD_CONFIRMED_DAY", day)
            confirm_hour = hour
            
        env.step(acts)
        
    rc41_mod._crop_plan = orig_crop_plan
    score = env.state[seat].observation.farms[seat].money
    return {
        "label": label,
        "seat": seat,
        "mode": portfolio_mode,
        "score": score,
        "confirm_day": confirm_day,
        "confirm_hour": confirm_hour
    }

def run_paired_match(match_args):
    label, r_path, s_val, seat = match_args
    res_ctrl = run_single_sim((label, r_path, s_val, seat, "2-carrots"))
    res_cand = run_single_sim((label, r_path, s_val, seat, "1-carrot-1-wheat"))
    return res_ctrl, res_cand

if __name__ == "__main__":
    match_tasks = []
    for r_name, opp_label in replays:
        p = os.path.join(r"reports/live_match_telemetry", r_name)
        for seat in (0, 1):
            match_tasks.append((opp_label, p, None, seat))
            
    for s_val, label in low_seeds:
        for seat in (0, 1):
            match_tasks.append((label, None, s_val, seat))
            
    print("=" * 135)
    print("PHASE 15: VECTOR 3 FULL 20-MATCH PAIRED GAUNTLET (CONTROL: 2 CARROTS vs CANDIDATE: 1 CARROT + 1 WHEAT)")
    print("=" * 135)
    print(f"{'MATCH / OPPONENT':<28} | {'SEAT':<4} | {'CONTROL (2C)':>13} | {'CANDIDATE (1C1W)':>16} | {'DELTA':>10} | {'CONFIRM':>11}")
    print("-" * 135)
    sys.stdout.flush()
    
    diffs = []
    ctrl_scores = []
    cand_scores = []
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_paired_match, match_tasks))
        
    for r_ctrl, r_cand in results:
        d = r_cand["score"] - r_ctrl["score"]
        diffs.append(d)
        ctrl_scores.append(r_ctrl["score"])
        cand_scores.append(r_cand["score"])
        c_str = f"D{r_cand['confirm_day']} H{r_cand['confirm_hour']}" if r_cand['confirm_day'] else "NO"
        print(f"{r_ctrl['label']:<28} | S{r_ctrl['seat']}  | ${r_ctrl['score']:>12,.0f} | ${r_cand['score']:>15,.0f} | ${d:>+9,.0f} | {c_str:>11}")
        sys.stdout.flush()
        
    print("=" * 135)
    print(f"{'Mean Score':<28} | {'-':<4} | ${sum(ctrl_scores)/len(ctrl_scores):>12,.0f} | ${sum(cand_scores)/len(cand_scores):>15,.0f} | ${sum(diffs)/len(diffs):>+9,.0f}")
    print(f"{'Global Suite Minimum':<28} | {'-':<4} | ${min(ctrl_scores):>12,.0f} | ${min(cand_scores):>15,.0f} | ${min(cand_scores) - min(ctrl_scores):>+9,.0f}")
    print(f"{'Maximum Ceiling':<28} | {'-':<4} | ${max(ctrl_scores):>12,.0f} | ${max(cand_scores):>15,.0f} | ${max(cand_scores) - max(ctrl_scores):>+9,.0f}")
    
    wins = sum(1 for x in diffs if x > 0)
    ties = sum(1 for x in diffs if x == 0)
    losses = sum(1 for x in diffs if x < 0)
    print(f"Candidate Record vs Control: Wins: {wins} | Losses: {losses} | Ties: {ties} (Tied or Won: {wins + ties}/20)")
    print("=" * 135)
