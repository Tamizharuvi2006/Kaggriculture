import os, json

replay_paths = [
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json",
]

# Add the other replays from reports/step5b/
step5b_dir = r"D:\kaggriculture\reports\step5b"
for root, dirs, files in os.walk(step5b_dir):
    for f in files:
        if f.endswith("-replay.json"):
            replay_paths.append(os.path.join(root, f))

print(f"Total full replay files to scan: {len(replay_paths)}")

records = []
for p in replay_paths:
    try:
        with open(p) as f: rep = json.load(f)
        steps = rep.get("steps", [])
        if len(steps) < 280: continue # need at least day 11
        
        obs_d11 = steps[11 * 24][0]["observation"]
        farms = obs_d11.get("farms", [])
        if len(farms) < 2: continue
        
        # Check both players' strawberry counts at Day 11 Hour 0
        s0 = sum(1 for r in farms[0]["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        s1 = sum(1 for r in farms[1]["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        
        # Check strawberry sales by player 0 and player 1 between Day 11 and Day 25
        sales = {0: 0, 1: 0}
        for s in range(11 * 24, min(25 * 24, len(steps)-1)):
            for pl in (0, 1):
                act = steps[s+1][pl].get("action", {})
                if isinstance(act, dict):
                    for o in act.get("market", []):
                        if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                            sales[pl] += o[2]
                            
        seed = rep.get("info", {}).get("seed", 0)
        fname = os.path.basename(p)
        records.append({
            "path": p,
            "fname": fname,
            "seed": seed,
            "s0_straw": s0,
            "s1_straw": s1,
            "s0_sales": sales[0],
            "s1_sales": sales[1]
        })
    except Exception as e:
        continue

print(f"Successfully processed {len(records)} full replays!\n")

print(f"{'FILENAME':<35} | {'SEED':<11} | {'P0 STRAW':>8} | {'P1 STRAW':>8} | {'P0 SALES':>8} | {'P1 SALES':>8}")
print("-" * 90)
for r in records[:25]:
    print(f"{r['fname']:<35} | {r['seed']:<11} | {r['s0_straw']:>8} | {r['s1_straw']:>8} | {r['s0_sales']:>8} | {r['s1_sales']:>8}")

print("=" * 90)
