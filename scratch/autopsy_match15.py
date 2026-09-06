import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_rc4_2_hybrid as rc42
import submission_rc5_d as rc5d

path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95511283\episode-95511283-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep['steps']
opp_actions = [steps[s][1].get('action') for s in range(1, len(steps))]

def trace_match(mod, name):
    env = kaggle_environments.make('kaggriculture', configuration={'episodeSteps': len(steps)-1, 'seed': rep['info']['seed']})
    env.reset()
    buys = []
    cash_by_day = {}
    animals_by_day = {}
    straws_by_day = {}
    unlocked_by_day = {}
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[0].observation
        day = obs['day']
        hour = obs['hour']
        act = mod.agent(obs)
        if isinstance(act, dict):
            for m in act.get('market', []):
                if m and m[0] in ('BUY_LAND', 'BUY_ANIMAL', 'BUY_SEED'):
                    if m[0] in ('BUY_LAND', 'BUY_ANIMAL') or (m[0] == 'BUY_SEED' and m[1] == 'STRAWBERRY'):
                        buys.append((day, hour, m))
        env.step([act, opp_actions[s]])
        f0 = env.state[0].observation['farms'][0]
        if hour == 23:
            cash_by_day[day] = f0['money']
            tiles = f0['tiles']
            animals_by_day[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get('animal') in ('COW', 'SHEEP'))
            straws_by_day[day] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get('crop') == 'STRAWBERRY')
            unlocked_by_day[day] = len(f0['unlocked_quadrants'])
            
    print(f"=== {name} TRACE (Final Money: ${f0['money']:,.0f}) ===")
    print("  Key Market Buys:", buys[:15])
    print("  Cash Days 4-12:   ", [round(cash_by_day.get(d, 0)) for d in range(4, 13)])
    print("  Animals Days 4-12:", [animals_by_day.get(d, 0) for d in range(4, 13)])
    print("  Strawberries D4-12:", [straws_by_day.get(d, 0) for d in range(4, 13)])
    print("  Unlocked Quads D4-12:", [unlocked_by_day.get(d, 0) for d in range(4, 13)])

trace_match(rc42, "RC4.2")
trace_match(rc5d, "RC5-D")
