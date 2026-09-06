import os, json
import pandas as pd

step5b_dir = r"D:\kaggriculture\reports\step5b"
replay_paths = [
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json",
]

for root, dirs, files in os.walk(step5b_dir):
    for f in files:
        if f.endswith("-replay.json"):
            replay_paths.append(os.path.join(root, f))

champions = []

for p in replay_paths:
    try:
        with open(p, "r", encoding="utf-8") as f:
            rep = json.load(f)
        steps = rep.get("steps", [])
        if not steps or len(steps) < 100: continue
        
        last_frame = steps[-1]
        for seat in (0, 1):
            money = last_frame[seat]["observation"]["farms"][seat]["money"]
            if money >= 90000:
                farm = last_frame[seat]["observation"]["farms"][seat]
                tiles = farm.get("tiles", [])
                unlocked = farm.get("unlocked_quadrants", [])
                
                # Count assets on last frame
                cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
                sheeps = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
                straws = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                melons = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "MELON")
                carrots = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "CARROT")
                wheats = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
                workers = len(farm.get("workers", []))
                
                # Analyze sales over episode
                sales = {}
                for step_idx in range(1, len(steps)):
                    act = steps[step_idx][seat].get("action", {})
                    if isinstance(act, dict):
                        for m_ord in act.get("market", []):
                            if len(m_ord) >= 3 and m_ord[0] == "SELL":
                                item, qty = m_ord[1], m_ord[2]
                                sales[item] = sales.get(item, 0) + qty
                                
                champions.append({
                    "replay": os.path.basename(p),
                    "seat": seat,
                    "money": money,
                    "workers": workers,
                    "unlocked": len(unlocked),
                    "cows": cows,
                    "sheeps": sheeps,
                    "straws": straws,
                    "melons": melons,
                    "carrots": carrots,
                    "wheats": wheats,
                    "sold_milk": sales.get("MILK", 0),
                    "sold_wool": sales.get("WOOL", 0),
                    "sold_straw": sales.get("STRAWBERRY", 0),
                    "sold_melon": sales.get("MELON", 0),
                    "sold_carrot": sales.get("CARROT", 0),
                    "sold_wheat": sales.get("WHEAT", 0),
                })
    except Exception as e:
        continue

df_champs = pd.DataFrame(champions).sort_values("money", ascending=False)
print("=" * 125)
print(f"ANATOMY OF 100K+ CHAMPIONS (FOUND {len(df_champs)} ELITE PERFORMANCES)")
print("=" * 125)
print(f"{'REPLAY':<25} | {'SEAT':<4} | {'FINAL $':>9} | {'W':>2} | {'UNL':>3} | {'COW':>3} | {'SHP':>3} | {'MILK':>5} | {'WOOL':>5} | {'STRAW':>5} | {'MEL':>4} | {'CAR':>5}")
print("-" * 125)
for _, r in df_champs.head(20).iterrows():
    print(f"{r['replay'][:25]:<25} | S{r['seat']}  | ${r['money']:>8,.0f} | {r['workers']:>2} | {r['unlocked']:>3} | {r['cows']:>3} | {r['sheeps']:>3} | {r['sold_milk']:>5} | {r['sold_wool']:>5} | {r['sold_straw']:>5} | {r['sold_melon']:>4} | {r['sold_carrot']:>5}")
print("=" * 125)
