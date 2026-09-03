import csv, gzip, json, os, sys, urllib.request

SEATS_CSV = r"D:\kaggriculture\data\hf_il\seats.csv"
CACHE_DIR = r"D:\kaggriculture\data\hf_il\cache"
OUT_REPORT = r"D:\kaggriculture\reports\behavioral_fingerprints_report.json"
os.makedirs(CACHE_DIR, exist_ok=True)

print("=" * 90)
print("     CROSS-TIER BEHAVIORAL FINGERPRINTING ENGINE (HUGGING FACE IL CORPUS)     ")
print("=" * 90)

# 1. Bucket episodes by final reward tier
tiers = {
    "Tier 1 (Sub-$60k)": [],
    "Tier 2 ($75k-$100k)": [],
    "Tier 3 ($105k-$125k)": [],
    "Tier 4 ($130k-$155k)": [],
}

with open(SEATS_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            rew = float(row.get("reward", 0))
            ep_id = int(row["episode_id"])
            seat = int(row["seat"])
            ag = row.get("agent", "")
            
            if rew < 60000:
                tiers["Tier 1 (Sub-$60k)"].append((ep_id, seat, ag, rew))
            elif 75000 <= rew <= 100000:
                tiers["Tier 2 ($75k-$100k)"].append((ep_id, seat, ag, rew))
            elif 105000 <= rew <= 125000:
                tiers["Tier 3 ($105k-$125k)"].append((ep_id, seat, ag, rew))
            elif 130000 <= rew:
                tiers["Tier 4 ($130k-$155k)"].append((ep_id, seat, ag, rew))
        except Exception:
            continue

print("Population Distribution in seats.csv:")
for t_name, lst in tiers.items():
    print(f"  - {t_name:<22}: {len(lst):>5} seats available")

# Select 4 distinct episodes per tier
sample_plan = {}
for t_name, lst in tiers.items():
    # pick evenly spaced episodes
    step = max(1, len(lst) // 4)
    sample_plan[t_name] = [lst[i * step] for i in range(4)]

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

def extract_fingerprint(steps, seat, agent_name, final_reward):
    # Trajectory tracking
    first_land_ne = None
    first_land_sw = None
    market_wheat_bought = 0
    fertilizer_sold = 0
    fertilizer_used = 0
    animal_deaths = 0
    
    opening_market = []
    worker_curve = {}
    animal_curve = {}
    crops_d04 = {}
    crops_d12 = {}
    crops_d20 = {}
    crops_d24 = {}
    cash_trajectory = {}
    
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
        
        cash = farm.get("money", 0)
        hands = len(farm.get("hands", []))
        unlocked = farm.get("unlocked_quadrants", ["NW"])
        
        if len(unlocked) >= 2 and first_land_ne is None:
            first_land_ne = day
        if len(unlocked) >= 3 and first_land_sw is None:
            first_land_sw = day
            
        animals = {"COW": 0, "SHEEP": 0}
        crops = {}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("animal") in animals:
                        animals[t["animal"]] += 1
                        if t.get("consecutive_unfed", 0) >= 2:
                            animal_deaths += 1
                    if t.get("crop"):
                        crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                        
        if hour == 0 and day in (0, 4, 8, 12, 16, 20, 24, 28):
            worker_curve[day] = hands
            animal_curve[day] = animals["COW"] + animals["SHEEP"]
            cash_trajectory[day] = int(cash)
            if day == 4: crops_d04 = crops
            elif day == 12: crops_d12 = crops
            elif day == 20: crops_d20 = crops
            elif day == 24: crops_d24 = crops
            
        act = step[seat].get("action", {}) or {}
        if s_idx <= 2:
            m_orders = act.get("market", []) or []
            if m_orders: opening_market.extend(m_orders)
            
        for order in act.get("market", []) or []:
            if order and len(order) >= 3:
                if order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                    market_wheat_bought += int(order[2])
                elif order[0] == "SELL" and order[1] == "FERTILIZER":
                    fertilizer_sold += int(order[2])
                    
        for h_act in act.get("hands", []) or []:
            if h_act and len(h_act) > 0 and h_act[0] == "FERTILIZE":
                fertilizer_used += 1
                
    return {
        "agent": agent_name,
        "final_reward": final_reward,
        "opening_orders": opening_market,
        "land_ne_day": first_land_ne,
        "land_sw_day": first_land_sw,
        "worker_curve": worker_curve,
        "animal_curve": animal_curve,
        "market_wheat_bought": market_wheat_bought,
        "fertilizer_sold": fertilizer_sold,
        "fertilizer_used": fertilizer_used,
        "animal_deaths": animal_deaths,
        "crops_d04": crops_d04,
        "crops_d12": crops_d12,
        "crops_d20": crops_d20,
        "crops_d24": crops_d24,
        "cash_trajectory": cash_trajectory,
    }

print("\nDownloading and Extracting Fingerprints...")
report_data = {}

for t_name, samples in sample_plan.items():
    print(f"\nProcessing {t_name}...")
    report_data[t_name] = []
    for ep_id, seat, ag, rew in samples:
        try:
            rep = fetch_replay(ep_id)
            fp = extract_fingerprint(rep["steps"], seat, ag, rew)
            report_data[t_name].append(fp)
            clean_ag = ag.encode("ascii", "replace").decode("ascii")
            print(f"  Ep {ep_id} ({clean_ag}): Final ${rew:,.0f} | Land NE: D{fp['land_ne_day']} SW: D{fp['land_sw_day']} | Market Wheat: {fp['market_wheat_bought']}")
        except Exception as e:
            print(f"  Ep {ep_id}: Error ({e})")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    json.dump(report_data, f, indent=2)

print(f"\nFingerprint report successfully saved to {OUT_REPORT}!")
