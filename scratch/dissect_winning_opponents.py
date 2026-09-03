import json
import glob

files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")

for fpath in files:
    with open(fpath, "r", encoding="utf-8") as fp:
        replay = json.load(fp)
    info = replay.get("info", {})
    eid = info.get("EpisodeId")
    agents = info.get("Agents", [])
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    opp_name = agents[opp_idx].get("Name")
    
    steps = replay.get("steps", [])
    print(f"\n{'='*80}\nEPISODE {eid} VS {opp_name} (Rewards: Hero ${replay.get('rewards')[hero_idx]:,.0f} vs Opp ${replay.get('rewards')[opp_idx]:,.0f})\n{'='*80}")
    
    # 1. Opponent Opening Move (Step 0)
    act_step0 = steps[1][opp_idx].get("action", {})
    print(f"Opening Move (Step 0): Farmer={act_step0.get('farmer')} | Market={act_step0.get('market')}")
    
    # 2. Quadrant Purchases
    lands = []
    hires = 0
    animals_bought = []
    
    for s in range(1, len(steps)):
        act = steps[s][opp_idx].get("action", {})
        for m in act.get("market", []):
            if isinstance(m, list) and len(m) > 0:
                if m[0] == "BUY_LAND":
                    lands.append((s // 24, s % 24))
                elif m[0] == "HIRE":
                    hires += 1
                elif m[0] == "BUY_ANIMAL":
                    animals_bought.append((s // 24, m[1], m[2] if len(m) > 2 else 1))
                    
    print(f"Total Lands Bought: {len(lands)} at days/hours {lands}")
    print(f"Total Animals Bought: {animals_bought}")
    print(f"Total Worker Hire Actions: {hires}")
    
    # 3. Final Farm Footprint
    final_farm = steps[-1][opp_idx].get("observation", {}).get("farms", [{}, {}])[opp_idx]
    crops = {}
    animals = {}
    for row in final_farm.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict):
                c = tile.get("crop")
                if c: crops[c] = crops.get(c, 0) + 1
                a = tile.get("animal")
                if a: animals[a] = animals.get(a, 0) + 1
    print(f"Final Crop Tiles: {crops}")
    print(f"Final Animal Tiles: {animals}")
    print(f"Final Unlocked Lands: {final_farm.get('unlocked_quadrants')}")
    print(f"Final Hands Count: {len(final_farm.get('hands', []))}")
