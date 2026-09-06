import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42
import submission_rc5_a_early_pasture as rc5a
import submission_rc5_b_labor_protected as rc5b

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
    cash_by_day = {}
    animals_by_day = {}
    
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
        if hour == 23:
            cash_by_day[day] = farm["money"]
            tiles = farm["tiles"]
            cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
            sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
            animals_by_day[day] = cows + sheep
            
    final_money = env.state[hero_seat].observation["farms"][hero_seat]["money"]
    return final_money, cash_by_day, animals_by_day, actions_counts

print("=" * 110)
print(f"{'REGIME':<26} | {'RC4.2 (Control)':<17} | {'RC5-A (Early Past)':<17} | {'RC5-B (Labor Prot)':<17} | {'DELTA (B vs 4.2)':<15} | {'DELTA (B vs A)':<15}")
print("=" * 110)

tot_42, tot_5a, tot_5b = 0, 0, 0

for path, seat, name in seeds_to_test:
    s_42, c_42, a_42, act_42 = run_agent_eval(rc42, path, seat)
    s_5a, c_5a, a_5a, act_5a = run_agent_eval(rc5a, path, seat)
    s_5b, c_5b, a_5b, act_5b = run_agent_eval(rc5b, path, seat)
    
    tot_42 += s_42
    tot_5a += s_5a
    tot_5b += s_5b
    
    d_b_42 = s_5b - s_42
    d_b_5a = s_5b - s_5a
    
    tag = "[WIN]" if d_b_42 > 0 else ("[TIE]" if d_b_42 == 0 else "[LOSS]")
    print(f"{name:<26} | ${s_42:>12,.0f}    | ${s_5a:>12,.0f}    | ${s_5b:>12,.0f}    | ${d_b_42:>+10,.0f} {tag:<6} | ${d_b_5a:>+10,.0f}")
    print(f"   > Day 4 Cash:   RC4.2=${c_42.get(4,0):,.0f} | RC5-A=${c_5a.get(4,0):,.0f} | RC5-B=${c_5b.get(4,0):,.0f}")
    print(f"   > Day 8 Animals: RC4.2={a_42.get(8,0)} animals | RC5-A={a_5a.get(8,0)} animals | RC5-B={a_5b.get(8,0)} animals")
    print(f"   > Total CARE:   RC4.2={act_42['CARE']} | RC5-A={act_5a['CARE']} | RC5-B={act_5b['CARE']}")
    print("-" * 110)

print("=" * 110)
print(f"{'SUITE TOTAL':<26} | ${tot_42:>12,.0f}    | ${tot_5a:>12,.0f}    | ${tot_5b:>12,.0f}    | ${tot_5b-tot_42:>+10,.0f}        | ${tot_5b-tot_5a:>+10,.0f}")
print(f"{'SUITE MEAN':<26}  | ${tot_42/4:>12,.0f}    | ${tot_5a/4:>12,.0f}    | ${tot_5b/4:>12,.0f}    | ${(tot_5b-tot_42)/4:>+10,.0f}        | ${(tot_5b-tot_5a)/4:>+10,.0f}")
print("=" * 110)
