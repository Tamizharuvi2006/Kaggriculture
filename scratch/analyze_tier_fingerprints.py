import json

with open(r"D:\kaggriculture\reports\behavioral_fingerprints_report.json", "r", encoding="utf-8") as f:
    report = json.load(f)

print("=" * 105)
print("     CROSS-TIER BEHAVIORAL COMPARISON (FINGERPRINT SYNTHESIS)     ")
print("=" * 105)

for tier_name, samples in report.items():
    print(f"\n>>> {tier_name} <<<")
    rewards = [s["final_reward"] for s in samples]
    avg_rew = sum(rewards) / len(rewards)
    
    # Opening orders
    first_orders = samples[0]["opening_orders"]
    
    # Worker curve average
    worker_days = [0, 4, 8, 12, 16, 20, 24, 28]
    avg_workers = {}
    for d in worker_days:
        vals = [s["worker_curve"].get(str(d), 0) for s in samples]
        avg_workers[d] = sum(vals) / len(vals)
        
    # Animal curve average
    avg_animals = {}
    for d in [4, 8, 12, 16, 20, 24]:
        vals = [s["animal_curve"].get(str(d), 0) for s in samples]
        avg_animals[d] = sum(vals) / len(vals)
        
    # Market wheat bought average
    m_wheat = [s["market_wheat_bought"] for s in samples]
    avg_m_wheat = sum(m_wheat) / len(m_wheat)
    
    # Fertilizer
    fert_sold = [s["fertilizer_sold"] for s in samples]
    fert_used = [s["fertilizer_used"] for s in samples]
    avg_fert_sold = sum(fert_sold) / len(fert_sold)
    avg_fert_used = sum(fert_used) / len(fert_used)
    
    # Crops at D12 and D24
    sample_c12 = samples[0]["crops_d12"]
    sample_c24 = samples[0]["crops_d24"]
    c12_str = " ".join(f"{c[:3]}:{n}" for c, n in sorted(sample_c12.items())) if sample_c12 else "-"
    c24_str = " ".join(f"{c[:3]}:{n}" for c, n in sorted(sample_c24.items())) if sample_c24 else "-"
    
    w_str = " ".join(f"D{d}:{avg_workers[d]:.1f}" for d in worker_days)
    a_str = " ".join(f"D{d}:{avg_animals[d]:.1f}" for d in [4, 8, 12, 16, 20, 24])
    
    print(f"  Average Reward : ${avg_rew:,.0f} (Range: ${min(rewards):,.0f} - ${max(rewards):,.0f})")
    print(f"  Opening Sample : {first_orders[:4]}")
    print(f"  Workers Curve  : {w_str}")
    print(f"  Animals Curve  : {a_str}")
    print(f"  Avg Mkt Wheat  : {avg_m_wheat:.0f} units")
    print(f"  Fertilizer     : Sold {avg_fert_sold:.0f} units | Used {avg_fert_used:.0f} units")
    print(f"  D12 Crops      : {c12_str}")
    print(f"  D24 Crops      : {c24_str}")
