import os, json

cache_dir = r"D:\kaggriculture\reports\live_match_telemetry\all_loss_replays_cache"
files = [f for f in os.listdir(cache_dir) if f.endswith(".json")]

print(f"Total cached replays found: {len(files)}")

records = []
for fname in files:
    fpath = os.path.join(cache_dir, fname)
    try:
        with open(fpath) as f:
            rep = json.load(f)
        steps = rep.get("steps", [])
        if len(steps) < 300: continue
        
        # Check Day 11 Hour 0 opponent strawberry count
        # Replays have 2 seats: let's inspect player 0 vs player 1
        s_d11 = 11 * 24
        obs0 = steps[s_d11][0]["observation"]
        f0 = obs0["farms"][0]
        f1 = obs0["farms"][1]
        
        s0_straw = sum(1 for r in f0["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        s1_straw = sum(1 for r in f1["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        
        # Check strawberry sales by player 1 from Day 11 to Day 25
        p1_straw_sold = 0
        for s in range(11 * 24, min(25 * 24, len(steps)-1)):
            act1 = steps[s+1][1].get("action", {})
            if isinstance(act1, dict):
                for o in act1.get("market", []):
                    if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                        p1_straw_sold += o[2]
                        
        records.append({
            "file": fname,
            "seed": rep.get("info", {}).get("seed", 0),
            "s1_straw_d11": s1_straw,
            "p1_straw_sold": p1_straw_sold
        })
    except Exception as e:
        continue

print(f"Successfully parsed {len(records)} replays!")

# Stratify into buckets
buckets = {
    "0-5 (Low)": [],
    "6-10 (Low-Mod)": [],
    "11-15 (Moderate)": [],
    "16-19 (Heavy)": [],
    "20-24 (Very Heavy)": [],
    "25+ (Extreme)": []
}

for r in records:
    c = r["s1_straw_d11"]
    if c <= 5: buckets["0-5 (Low)"].append(r)
    elif c <= 10: buckets["6-10 (Low-Mod)"].append(r)
    elif c <= 15: buckets["11-15 (Moderate)"].append(r)
    elif c <= 19: buckets["16-19 (Heavy)"].append(r)
    elif c <= 24: buckets["20-24 (Very Heavy)"].append(r)
    else: buckets["25+ (Extreme)"].append(r)

print("\nSTRATIFIED OPPONENT STRAWBERRY EXPOSURE DISTRIBUTION:")
for b_name, b_list in buckets.items():
    print(f"  {b_name:<20}: {len(b_list)} replays available")
    if b_list:
        sample = b_list[0]
        print(f"     Sample: {sample['file']} | Seed: {sample['seed']} | D11 Straw: {sample['s1_straw_d11']} | Sold D11-25: {sample['p1_straw_sold']}")
