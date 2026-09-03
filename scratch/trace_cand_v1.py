import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments, json
import candidates.submission_adaptive_v2_economic as cand

replay_file = r'D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json'
with open(replay_file) as f: rep = json.load(f)

opp_actions = [frame[1].get('action') for frame in rep['steps'][1:]]
env = kaggle_environments.make('kaggriculture', configuration={'episodeSteps': 720, 'seed': rep['info']['seed']})
env.reset()

for s in range(len(opp_actions)):
    if env.done: break
    act = cand.agent(env.state[0].observation)
    env.step([act, opp_actions[s]])
    
    if s % 48 == 0 or s == len(opp_actions) - 1:
        f0 = env.state[0].observation['farms'][0]
        tiles = f0['tiles']
        kinds = {}
        crops = {}
        unwatered = 0
        cows = 0
        for r in tiles:
            for t in r:
                if isinstance(t, dict):
                    k = t.get('kind')
                    kinds[k] = kinds.get(k, 0) + 1
                    if t.get('animal') == 'COW': cows += 1
                    if k == 'PLANT':
                        c = t.get('crop')
                        crops[c] = crops.get(c, 0) + 1
                        if not t.get('watered_today', False): unwatered += 1
        print(f"D{s//24:02d}:H{s%24:02d} | Cash: ${f0['money']:6.0f} | Hands: {len(f0.get('hands', [])):2d} | Cows: {cows} | Plants: {kinds.get('PLANT', 0):2d} {crops} | Unwatered: {unwatered}")

print("Cand V1 Final:", env.state[0].reward, "Opp:", env.state[1].reward)
