import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_rc4_2_hybrid as rc42
import submission_rc5_g1 as rc5g1

seeds = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Champion Seed (91697084)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1, "Soumi Flooder (104388418)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1, "Arao Passive (104379472)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1, "High Ceiling (104475527)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 1, "Match 5 (C1 Collapse Seed)"),
]

def run(mod, path, seat):
    with open(path) as f: rep = json.load(f)
    steps = rep['steps']
    opp = [steps[s][1-seat].get('action') for s in range(1, len(steps))]
    env = kaggle_environments.make('kaggriculture', configuration={'episodeSteps': len(steps)-1, 'seed': rep['info']['seed']})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[seat].observation
        act = mod.agent(obs)
        if seat == 0: env.step([act, opp[s]])
        else: env.step([opp[s], act])
    return int(env.state[seat].observation['farms'][seat]['money'])

print("=" * 85)
print(f"{'REGIME':<30} | {'RC4.2':<12} | {'RC5-G1':<12} | {'DELTA'}")
print("-" * 85)
for p, s, name in seeds:
    m42 = run(rc42, p, s)
    mg = run(rc5g1, p, s)
    d = mg - m42
    tag = '[WIN]' if d > 0 else ('[TIE]' if d == 0 else '[LOSS]')
    print(f"{name:<30} | ${m42:>10,} | ${mg:>10,} | ${d:>+10,} {tag}")
print("=" * 85)
