import csv, gzip, json, os, sys, urllib.request

INDEX_CSV = r"D:\kaggriculture\data\hf_il\index.csv"
OUT_REPORT = r"D:\kaggriculture\reports\replay_failure_miner_report.json"

print("=" * 80)
print("     REPLAY FAILURE MINER: ELO-STRATIFIED GRANDMASTER ARCHAEOLOGY     ")
print("=" * 80)

# 1. Read index.csv to categorize matches by Elo tiers
tier_matches = {
    "tier_sub_1000": [],
    "tier_1000_1400": [],
    "tier_1400_2000": [],
    "tier_3000_plus": [],
}

with open(INDEX_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            elo = float(row.get("elo_avg", 0))
            ep_id = int(row["episode_id"])
            if elo < 1000:
                tier_matches["tier_sub_1000"].append(row)
            elif 1000 <= elo < 1400:
                tier_matches["tier_1000_1400"].append(row)
            elif 1400 <= elo < 2000:
                tier_matches["tier_1400_2000"].append(row)
            elif elo >= 2800:
                tier_matches["tier_3000_plus"].append(row)
        except Exception:
            continue

print(f"Total Matches in Index: {sum(len(v) for v in tier_matches.values())}")
for k, v in tier_matches.items():
    print(f"  - {k:<16}: {len(v):>5} matches available")

# 2. Select a representative sample from each tier
sample_targets = {
    "tier_1000_1400": tier_matches["tier_1000_1400"][:8],
    "tier_3000_plus": tier_matches["tier_3000_plus"][:12],
}

def fetch_replay(ep_id):
    local_dir = r"D:\kaggriculture\data\hf_il\cache"
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, f"{ep_id}.json.gz")
    if not os.path.exists(local_path):
        bucket = str(ep_id)[-2:]
        url = f"https://huggingface.co/datasets/KiroSamurai/kaggriculture-il/resolve/main/datasets/il/episodes/{bucket}/{ep_id}.json.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(local_path, "wb") as out:
            out.write(resp.read())
    with gzip.open(local_path, "rt", encoding="utf-8") as f:
        return json.load(f)

def analyze_seat(steps, seat, name, elo):
    rewards = [s[seat].get("reward", 0) for s in steps]
    final_reward = rewards[-1] if rewards else 0
    
    first_animal_day = None
    first_land_day = None
    max_workers = 0
    worker_curve = {}
    market_wheat_bought = 0
    animal_counts_by_day = {}
    crop_profile_d12 = {}
    
    for s_idx, step in enumerate(steps):
        day = s_idx // 24
        hour = s_idx % 24
        obs = step[seat].get("observation", {})
        if not obs: continue
        farms = obs.get("farms", [])
        if len(farms) <= seat: continue
        farm = farms[seat]
        tiles = farm.get("tiles", [])
        
        hands = len(farm.get("hands", []))
        if hands > max_workers: max_workers = hands
        if hour == 0 and day in (0, 4, 8, 12, 16, 20, 24, 28):
            worker_curve[day] = hands
            
        unlocked = farm.get("unlocked_quadrants", ["NW"])
        if len(unlocked) > 1 and first_land_day is None:
            first_land_day = day
            
        # Count animals & crops
        animals = 0
        crops = {}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("animal"): animals += 1
                    if t.get("crop"): crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                    
        if animals > 0 and first_animal_day is None:
            first_animal_day = day
            
        if hour == 0 and day in (4, 8, 12, 16, 20, 24):
            animal_counts_by_day[day] = animals
            if day == 12: crop_profile_d12 = crops
            
        # Check market actions
        act = step[seat].get("action", {}) or {}
        market_orders = act.get("market", []) or []
        for order in market_orders:
            if order and len(order) >= 3:
                if order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                    market_wheat_bought += int(order[2])
                    
    return {
        "seat": seat,
        "name": name,
        "elo": elo,
        "final_reward": final_reward,
        "first_animal_day": first_animal_day,
        "first_land_day": first_land_day,
        "max_workers": max_workers,
        "worker_curve": worker_curve,
        "market_wheat_bought": market_wheat_bought,
        "animal_counts_by_day": animal_counts_by_day,
        "crop_profile_d12": crop_profile_d12,
    }

print("\nMining Replays Across Elo Tiers...")
tier_analyses = {}

for tier, rows in sample_targets.items():
    print(f"\nProcessing {tier} ({len(rows)} matches)...")
    tier_analyses[tier] = []
    for r in rows:
        ep_id = int(r["episode_id"])
        try:
            rep = fetch_replay(ep_id)
            steps = rep.get("steps", [])
            s0 = analyze_seat(steps, 0, r["agent0"], float(r.get("elo_avg", 0)))
            s1 = analyze_seat(steps, 1, r["agent1"], float(r.get("elo_avg", 0)))
            tier_analyses[tier].extend([s0, s1])
            print(f"  Ep {ep_id}: {s0['name']} (${s0['final_reward']:,.0f}) vs {s1['name']} (${s1['final_reward']:,.0f})")
        except Exception as e:
            print(f"  Ep {ep_id}: Failed ({e})")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    json.dump(tier_analyses, f, indent=2)

print(f"\nAnalysis saved to {OUT_REPORT}!")
