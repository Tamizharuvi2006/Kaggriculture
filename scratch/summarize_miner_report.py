import json

with open(r"D:\kaggriculture\reports\replay_failure_miner_report.json", "r", encoding="utf-8") as f:
    data = json.load(f)

tier_data = data.get("tier_3000_plus", [])

print("=" * 95)
print("     GRANDMASTER (3000+ ELO) STRATEGY PROFILE (10 MATCHES MINED)     ")
print("=" * 95)

for s in tier_data:
    name = s["name"]
    reward = s["final_reward"]
    anim_d = s["first_animal_day"]
    land_d = s["first_land_day"]
    max_w = s["max_workers"]
    m_wheat = s["market_wheat_bought"]
    w_curve = s["worker_curve"]
    crops = s["crop_profile_d12"]
    
    crop_str = " ".join(f"{c[:3]}:{n}" for c, n in crops.items()) if crops else "None"
    
    # Format worker curve
    w_str = " ".join(f"D{d}:{w}" for d, w in sorted(w_curve.items()))
    
    # Safe name encoding for Windows terminal
    clean_name = name.encode("ascii", "replace").decode("ascii")
    print(f"[{clean_name:<18}] Reward: ${reward:>7,.0f} | 1st Land: D{land_d} | 1st Animal: D{anim_d} | Max Workers: {max_w:>2}")
    print(f"                     Worker Curve : {w_str}")
    print(f"                     Market Wheat : {m_wheat} units | D12 Crops: {crop_str}")
    print("-" * 95)
