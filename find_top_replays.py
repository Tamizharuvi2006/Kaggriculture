import json
import glob
import os

all_replays = glob.glob("D:/kaggriculture/**/*.json", recursive=True)

elite_replays = []

for r_path in all_replays:
    if "episode-" not in r_path or not r_path.endswith(".json"):
        continue
    try:
        with open(r_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        steps = data.get("steps", [])
        if not steps:
            continue
            
        last_step = steps[-1]
        p0_rew = last_step[0].get("reward", 0.0) or 0.0
        p1_rew = last_step[1].get("reward", 0.0) or 0.0
        
        max_rew = max(p0_rew, p1_rew)
        if max_rew >= 100000.0:
            winner = 0 if p0_rew > p1_rew else 1
            elite_replays.append({
                "path": r_path,
                "p0_rew": p0_rew,
                "p1_rew": p1_rew,
                "max_rew": max_rew,
                "winner": winner,
                "steps_len": len(steps)
            })
    except Exception as e:
        continue

elite_replays.sort(key=lambda x: x["max_rew"], reverse=True)

print(f"Found {len(elite_replays)} elite replays with Reward >= $100k:")
for i, r in enumerate(elite_replays[:20]):
    print(f"[{i+1:2d}] Max: ${r['max_rew']:8.1f} | P0: ${r['p0_rew']:8.1f} | P1: ${r['p1_rew']:8.1f} | Winner: P{r['winner']} | {os.path.basename(r['path'])}")
