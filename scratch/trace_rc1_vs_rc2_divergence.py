import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, kaggle_environments
import submission_rc1_ev_dispatcher as rc1
import submission_rc2_terminal_horizon as rc2

def trace_match(replay_file, opp_label, cand_seat=0):
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", replay_file)
    with open(path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
    
    traces = {}
    for agent_name, agent_mod in [("RC1", rc1), ("RC2", rc2)]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
        env.reset()
        
        day_snapshots = {}
        for s in range(len(opp_actions)):
            if env.done: break
            day = s // 24
            hour = s % 24
            obs = env.state[cand_seat].observation
            
            if hour == 0 and day in (0, 4, 8, 12, 16, 20, 24, 28):
                farm = obs["farms"][cand_seat]
                cash = farm.get("money", 0)
                crops = {}
                for row in farm.get("tiles", []):
                    for t in row:
                        if isinstance(t, dict) and t.get("crop"):
                            c = t["crop"]
                            crops[c] = crops.get(c, 0) + 1
                crop_s = " ".join(f"{k[:3]}:{v}" for k, v in sorted(crops.items())) if crops else "None"
                day_snapshots[day] = {"cash": int(cash), "crops": crop_s}
                
            act = agent_mod.agent(obs)
            joint = [None, None]
            joint[cand_seat] = act
            joint[1 - cand_seat] = opp_actions[s]
            env.step(joint)
            
        traces[agent_name] = {
            "reward": env.state[cand_seat].reward,
            "snapshots": day_snapshots,
        }
        
    print("=" * 95)
    print(f"     DIVERGENCE TRACE: {opp_label} (RC1: ${traces['RC1']['reward']:,.0f} vs RC2: ${traces['RC2']['reward']:,.0f})     ")
    print("=" * 95)
    for day in (0, 4, 8, 12, 16, 20, 24, 28):
        s1 = traces["RC1"]["snapshots"].get(day, {})
        s2 = traces["RC2"]["snapshots"].get(day, {})
        c1 = s1.get("cash", 0)
        c2 = s2.get("cash", 0)
        diff = c2 - c1
        print(f"D{day:02d} | RC1: Cash ${c1:>7,d} [{s1.get('crops', '')}]")
        print(f"    | RC2: Cash ${c2:>7,d} [{s2.get('crops', '')}] -> Diff: ${diff:+7,d}")
        print("-" * 95)

trace_match("episode-104388418-replay.json", "Soumi Ghosh (+15,310 WIN)")
trace_match("episode-104424149-replay.json", "JZ (-911 LOSS)")
