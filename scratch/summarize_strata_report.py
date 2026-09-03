import json

with open(r"D:\kaggriculture\reports\statistical_behavior_miner_report.json", "r", encoding="utf-8") as f:
    report = json.load(f)

print("=" * 110)
print("     STATISTICAL PROFILE ACROSS PERFORMANCE STRATA (MEAN VALUES)     ")
print("=" * 110)
print(f"{'Metric':<25} | {'Band 1 (<$70k)':<15} | {'Band 2 ($70k-$95k)':<18} | {'Band 3 ($95k-$115k)':<19} | {'Band 4 ($115k-$135k)':<20} | {'Band 5 ($135k+)':<15}")
print("-" * 110)

metrics = [
    ("final_reward", "Reward ($)"),
    ("day0_cash_left", "D0 Cash Left ($)"),
    ("day0_animals", "D0 Animals"),
    ("first_production_day", "1st Animal Prod (Day)"),
    ("day_land_ne", "Land NE (Day)"),
    ("day_land_sw", "Land SW (Day)"),
    ("workers_d8", "Workers at D8"),
    ("strawberries_d16", "Strawberries at D16"),
    ("animals_d16", "Animals at D16"),
    ("market_wheat_total", "Market Wheat (Units)"),
    ("sales_count_total", "Total Sale Events"),
    ("fast_d24", "D24 Fast Crops"),
]

for m_key, m_label in metrics:
    row_vals = []
    for b_name in ["Band 1 (<$70k)", "Band 2 ($70k-$95k)", "Band 3 ($95k-$115k)", "Band 4 ($115k-$135k)", "Band 5 ($135k+)"]:
        samples = report[b_name]
        if m_key == "final_reward":
            vals = [s["reward"] for s in samples]
        elif m_key == "fast_d24":
            vals = [s["wheat_d24"] + s["carrot_d24"] for s in samples]
        else:
            vals = [s[m_key] for s in samples]
        avg = sum(vals) / len(vals)
        if "Reward" in m_label or "Cash" in m_label:
            row_vals.append(f"${avg:>10,.0f}")
        elif "Day" in m_label or "D8" in m_label or "Animals" in m_label or "Strawberries" in m_label or "Crops" in m_label:
            row_vals.append(f"{avg:>10.1f}")
        else:
            row_vals.append(f"{avg:>10.0f}")
    print(f"{m_label:<25} | {row_vals[0]:<15} | {row_vals[1]:<18} | {row_vals[2]:<19} | {row_vals[3]:<20} | {row_vals[4]:<15}")

print("=" * 110)
