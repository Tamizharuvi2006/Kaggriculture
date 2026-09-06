import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42
import submission_rc5_a_early_pasture as rc5a

seeds_to_test = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Champion Seed (91697084)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1, "Soumi Flooder (104388418)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1, "Arao Passive (104379472)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1, "High Ceiling (104475527)"),
]

def run_agent_eval(agent_mod, rep_path, hero_seat):
    with open(rep_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    actions_counts = Counter()
    milestones = {}
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        
        act = agent_mod.agent(obs)
        if isinstance(act, dict):
            for h in act.get("hands", []):
                if h: actions_counts[h[0]] += 1
                
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
            
        farm = env.state[hero_seat].observation["farms"][hero_seat]
        if hour == 23 and day in (4, 8, 11, 28):
            tiles = farm["tiles"]
            cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
            sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
            pastures = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE")
            milestones[day] = {
                "cows": cows, "sheep": sheep, "pastures": pastures,
                "money": farm["money"],
                "pass": actions_counts["PASS"],
                "care": actions_counts["CARE"],
                "feed": actions_counts["FEED"],
                "fert": actions_counts["COLLECT_FERTILIZER"]
            }
            
    final_money = env.state[hero_seat].observation["farms"][hero_seat]["money"]
    return final_money, milestones, actions_counts

print("=" * 110)
print("RC5-A SINGLE-VARIABLE EXPERIMENT: REMOVE NW PASTURE ACTIVATION GATE ONLY")
print("=" * 110)

for path, seat, name in seeds_to_test:
    print(f"\n>>> REGIME: {name}")
    score_rc42, ms_rc42, acts_rc42 = run_agent_eval(rc42, path, seat)
    score_rc5a, ms_rc5a, acts_rc5a = run_agent_eval(rc5a, path, seat)
    delta = score_rc5a - score_rc42
    tag = "[WIN]" if delta > 0 else ("[TIE]" if delta == 0 else "[LOSS]")
    print(f"  Final Score: RC4.2 = ${score_rc42:,.0f} | RC5-A = ${score_rc5a:,.0f} | Delta = ${delta:+,.0f} {tag}")
    print(f"  Pastures at Day 4: RC4.2 = {ms_rc42.get(4,{}).get('pastures',0)} | RC5-A = {ms_rc5a.get(4,{}).get('pastures',0)}")
    print(f"  Animals at Day 4:  RC4.2 = {ms_rc42.get(4,{}).get('cows',0)+ms_rc42.get(4,{}).get('sheep',0)} | RC5-A = {ms_rc5a.get(4,{}).get('cows',0)+ms_rc5a.get(4,{}).get('sheep',0)}")
    print(f"  Animals at Day 8:  RC4.2 = {ms_rc42.get(8,{}).get('cows',0)+ms_rc42.get(8,{}).get('sheep',0)} | RC5-A = {ms_rc5a.get(8,{}).get('cows',0)+ms_rc5a.get(8,{}).get('sheep',0)}")
    print(f"  Animals at Day 11: RC4.2 = {ms_rc42.get(11,{}).get('cows',0)+ms_rc42.get(11,{}).get('sheep',0)} | RC5-A = {ms_rc5a.get(11,{}).get('cows',0)+ms_rc5a.get(11,{}).get('sheep',0)}")
    print(f"  Total CARE Actions: RC4.2 = {acts_rc42['CARE']} | RC5-A = {acts_rc5a['CARE']}")
    print(f"  Total PASS Actions: RC4.2 = {acts_rc42['PASS']} | RC5-A = {acts_rc5a['PASS']}")
print("=" * 110)
