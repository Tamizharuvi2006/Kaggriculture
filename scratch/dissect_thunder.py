import gzip, json

replay_path = r"D:\kaggriculture\data\hf_il\cache\90563876.json.gz"
with gzip.open(replay_path, "rt", encoding="utf-8") as f:
    rep = json.load(f)

steps = rep["steps"]
rewards = rep["rewards"]

print("=" * 85)
print(f"     DEEP DIVE: THUNDER THUNDER (${rewards[0]:,.0f}) vs Raj Aryan (${rewards[1]:,.0f})     ")
print("=" * 85)

for day in (0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28):
    step_idx = day * 24
    if step_idx >= len(steps): break
    step = steps[step_idx]
    
    for seat, name in ((0, "THUNDER THUNDER"), (1, "Raj Aryan")):
        obs = step[seat].get("observation", {})
        farm = obs.get("farms", [])[seat]
        priv = obs.get("private", {}) or {}
        shed = priv.get("shed", {}) or {}
        
        cash = farm.get("money", 0)
        hands = len(farm.get("hands", []))
        unlocked = farm.get("unlocked_quadrants", ["NW"])
        
        animals = {"COW": 0, "SHEEP": 0}
        crops = {}
        for row in farm.get("tiles", []):
            for t in row:
                if isinstance(t, dict):
                    if t.get("animal") in animals: animals[t["animal"]] += 1
                    if t.get("crop"): crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                    
        crop_summary = " ".join(f"{c[:3]}:{n}" for c, n in sorted(crops.items())) if crops else "-"
        anim_summary = f"C:{animals['COW']} S:{animals['SHEEP']} (Shed:{int(shed.get('COW',0))+int(shed.get('SHEEP',0))})"
        
        print(f"D{day:02d} | [{name:<15}] Cash: ${cash:>7,.0f} | Hands: {hands:>2} | Lands: {len(unlocked)} | Animals: {anim_summary:<18} | Crops: {crop_summary}")
    print("-" * 85)
