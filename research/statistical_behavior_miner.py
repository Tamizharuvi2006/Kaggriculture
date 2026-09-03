import csv, gzip, json, os, sys, urllib.request

SEATS_CSV = r"D:\kaggriculture\data\hf_il\seats.csv"
CACHE_DIR = r"D:\kaggriculture\data\hf_il\cache"
OUT_REPORT = r"D:\kaggriculture\reports\statistical_behavior_miner_report.json"
os.makedirs(CACHE_DIR, exist_ok=True)

print("=" * 100)
print("     STATISTICAL BEHAVIOR MINER: CROSS-STRATA FREQUENCY ANALYSIS     ")
print("=" * 100)

bands = {
    "Band 1 (<$70k)": [],
    "Band 2 ($70k-$95k)": [],
    "Band 3 ($95k-$115k)": [],
    "Band 4 ($115k-$135k)": [],
    "Band 5 ($135k+)": [],
}

with open(SEATS_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            rew = float(row.get("reward", 0))
            ep_id = int(row["episode_id"])
            seat = int(row["seat"])
            ag = row.get("agent", "")
            
            if rew < 70000:
                bands["Band 1 (<$70k)"].append((ep_id, seat, ag, rew))
            elif 70000 <= rew < 95000:
                bands["Band 2 ($70k-$95k)"].append((ep_id, seat, ag, rew))
            elif 95000 <= rew < 115000:
                bands["Band 3 ($95k-$115k)"].append((ep_id, seat, ag, rew))
            elif 115000 <= rew < 135000:
                bands["Band 4 ($115k-$135k)"].append((ep_id, seat, ag, rew))
            else:
                bands["Band 5 ($135k+)"].append((ep_id, seat, ag, rew))
        except Exception:
            continue

print("Population Distribution:")
for b_name, lst in bands.items():
    print(f"  - {b_name:<20}: {len(lst):>5} seats available")

# Sample 6 distinct episodes per band (30 episodes total)
sample_plan = {}
for b_name, lst in bands.items():
    step = max(1, len(lst) // 6)
    sample_plan[b_name] = [lst[i * step] for i in range(6)]

def fetch_replay(ep_id):
    local_path = os.path.join(CACHE_DIR, f"{ep_id}.json.gz")
    if not os.path.exists(local_path):
        bucket = str(ep_id)[-2:]
        url = f"https://huggingface.co/datasets/KiroSamurai/kaggriculture-il/resolve/main/datasets/il/episodes/{bucket}/{ep_id}.json.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(local_path, "wb") as out:
            out.write(resp.read())
    with gzip.open(local_path, "rt", encoding="utf-8") as f:
        return json.load(f)

def extract_stats(steps, seat, ag, rew):
    day0_cash_left = 3000
    day0_animals = 0
    day0_crops = 0
    
    first_production_day = None
    day_land_ne = None
    day_land_sw = None
    workers_d8 = 0
    
    strawberries_d16 = 0
    animals_d16 = 0
    market_wheat_total = 0
    sales_count_total = 0
    
    wheat_d24 = 0
    carrot_d24 = 0
    
    for s_idx, step in enumerate(steps):
        day = s_idx // 24
        hour = s_idx % 24
        obs = step[seat].get("observation", {})
        if not obs: continue
        farms = obs.get("farms", [])
        if len(farms) <= seat: continue
        farm = farms[seat]
        tiles = farm.get("tiles", [])
        priv = obs.get("private", {}) or {}
        shed = priv.get("shed", {}) or {}
        
        unlocked = farm.get("unlocked_quadrants", ["NW"])
        if len(unlocked) >= 2 and day_land_ne is None: day_land_ne = day
        if len(unlocked) >= 3 and day_land_sw is None: day_land_sw = day
        
        # Day 0 state (hour 1)
        if day == 0 and hour == 1:
            day0_cash_left = int(farm.get("money", 0))
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("animal"): day0_animals += 1
                        if t.get("crop"): day0_crops += 1
            day0_animals += int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
            
        # First animal production
        if first_production_day is None:
            inv = priv.get("inventory", {}) or {}
            if int(inv.get("MILK", 0)) > 0 or int(inv.get("WOOL", 0)) > 0:
                first_production_day = day
                
        # Day 8 workers
        if day == 8 and hour == 1:
            workers_d8 = len(farm.get("hands", []))
            
        # Day 16 state
        if day == 16 and hour == 0:
            anims = 0
            straws = 0
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("animal"): anims += 1
                        if t.get("crop") == "STRAWBERRY": straws += 1
            animals_d16 = anims + int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
            strawberries_d16 = straws
            
        # Day 24 terminal crops
        if day == 24 and hour == 0:
            w_count = 0
            c_count = 0
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("crop") == "WHEAT": w_count += 1
                        elif t.get("crop") == "CARROT": c_count += 1
            wheat_d24 = w_count
            carrot_d24 = c_count
            
        # Market orders
        act = step[seat].get("action", {}) or {}
        for m in act.get("market", []) or []:
            if m and len(m) >= 3:
                if m[0] == "BUY_PRODUCT" and m[1] == "WHEAT":
                    market_wheat_total += int(m[2])
                elif m[0] == "SELL":
                    sales_count_total += 1
                    
    return {
        "agent": ag,
        "reward": rew,
        "day0_cash_left": day0_cash_left,
        "day0_animals": day0_animals,
        "day0_crops": day0_crops,
        "first_production_day": first_production_day if first_production_day is not None else 28,
        "day_land_ne": day_land_ne if day_land_ne is not None else 28,
        "day_land_sw": day_land_sw if day_land_sw is not None else 28,
        "workers_d8": workers_d8,
        "animals_d16": animals_d16,
        "strawberries_d16": strawberries_d16,
        "market_wheat_total": market_wheat_total,
        "sales_count_total": sales_count_total,
        "wheat_d24": wheat_d24,
        "carrot_d24": carrot_d24,
    }

print("\nMining Replays Across Strata...")
extracted_data = {}

for b_name, samples in sample_plan.items():
    print(f"\nProcessing {b_name}...")
    extracted_data[b_name] = []
    for ep_id, seat, ag, rew in samples:
        try:
            rep = fetch_replay(ep_id)
            stats = extract_stats(rep["steps"], seat, ag, rew)
            extracted_data[b_name].append(stats)
            clean_ag = ag.encode("ascii", "replace").decode("ascii")
            print(f"  Ep {ep_id} ({clean_ag:<18}): ${rew:>7,.0f} | D0 Anim:{stats['day0_animals']} | Land NE:D{stats['day_land_ne']} | StrwD16:{stats['strawberries_d16']} | D24 Fast:{stats['wheat_d24']+stats['carrot_d24']}")
        except Exception as e:
            print(f"  Ep {ep_id}: Error ({e})")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    json.dump(extracted_data, f, indent=2)

print(f"\nAnalysis saved to {OUT_REPORT}!")
