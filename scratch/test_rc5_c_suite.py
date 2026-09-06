import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42
import submission_rc5_a_early_pasture as rc5a
import submission_rc5_c1_day_gate as rc5c1
import submission_rc5_c2_reserve_200 as rc5c2
import submission_rc5_c3_champion_expansion as rc5c3

seeds_to_test = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Champion Seed (91697084)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1, "Soumi Flooder (104388418)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1, "Arao Passive (104379472)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1, "High Ceiling (104475527)"),
]

variants = [
    ("RC4.2 (Control)", rc42),
    ("RC5-A (Pasture Only)", rc5a),
    ("RC5-C1 (No Day Gate)", rc5c1),
    ("RC5-C2 (Reserve $200)", rc5c2),
    ("RC5-C3 (Both)", rc5c3),
]

def eval_candidate(agent_mod, rep_path, hero_seat):
    with open(rep_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    ne_day, sw_day = None, None
    d11_animals = 0
    d11_straws = 0
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        
        act = agent_mod.agent(obs)
        if hero_seat == 0: env.step([act, opp_actions[s]])
        else: env.step([opp_actions[s], act])
        
        farm = env.state[hero_seat].observation["farms"][hero_seat]
        unlocked = farm["unlocked_quadrants"]
        if "NE" in unlocked and ne_day is None: ne_day = day
        if "SW" in unlocked and sw_day is None: sw_day = day
        
        if day == 11 and hour == 0:
            tiles = farm["tiles"]
            d11_animals = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"))
            d11_straws = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            
    final_money = env.state[hero_seat].observation["farms"][hero_seat]["money"]
    return int(final_money), ne_day, sw_day, d11_animals, d11_straws

print("=" * 120)
print(f"{'REGIME':<26} | {'RC4.2':<12} | {'RC5-A':<12} | {'RC5-C1':<12} | {'RC5-C2':<12} | {'RC5-C3':<12}")
print("=" * 120)

totals = {name: 0 for name, _ in variants}

for rep_path, seat, name in seeds_to_test:
    row_str = f"{name:<26} | "
    row_details = []
    for var_name, mod in variants:
        score, ne, sw, a11, s11 = eval_candidate(mod, rep_path, seat)
        totals[var_name] += score
        row_str += f"${score:>10,} | "
        row_details.append(f"{var_name}: NE=D{ne} SW=D{sw} (D11: {a11} anim, {s11} straw)")
    print(row_str)
    for d in row_details:
        print(f"   > {d}")
    print("-" * 120)

print("=" * 120)
mean_str = f"{'SUITE MEAN':<26} | "
for var_name, _ in variants:
    m = totals[var_name] / len(seeds_to_test)
    mean_str += f"${m:>10,.0f} | "
print(mean_str)
print("=" * 120)
