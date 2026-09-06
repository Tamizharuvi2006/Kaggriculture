import os, glob, json

telemetry_dir = r"D:\kaggriculture\reports\live_match_telemetry"
replays = glob.glob(os.path.join(telemetry_dir, "**", "*replay*.json"), recursive=True)
print(f"Total replay JSONs in live_match_telemetry: {len(replays)}")

valid_traces = 0
total_steps = 0
for r in replays:
    try:
        size = os.path.getsize(r)
        if size < 100_000: continue # Skip tiny metadata files
        with open(r, "r") as f:
            data = json.load(f)
            steps = data.get("steps", [])
            if len(steps) >= 100:
                valid_traces += 1
                total_steps += len(steps)
    except Exception as e:
        pass

print(f"Valid full-game replay traces: {valid_traces}")
print(f"Total game steps available: {total_steps:,}")

# Also check CSV datasets in data/
csvs = glob.glob(r"D:\kaggriculture\data\*.csv")
print(f"CSV datasets in data/: {len(csvs)}")
for c in csvs:
    print(f"  {os.path.basename(c)}: {os.path.getsize(c):,} bytes")
