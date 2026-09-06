import json

with open(r"D:\kaggriculture\reports\DAY0_12_CASHFLOW_FORENSICS.json") as f:
    data = json.load(f)

for target, days in data.items():
    print("=" * 80)
    print(f"TARGET: {target}")
    print("=" * 80)
    for d in range(6, 13):
        info = days.get(str(d), {})
        print(f"Day {d:02d}: Start: ${info.get('start_cash', 0):>5,.0f} | Min: ${info.get('min_cash', 0):>5,.0f} | End: ${info.get('end_cash', 0):>5,.0f} | SeedSpent: ${info.get('seed_spent', 0):>5,.0f} | CropRev: ${info.get('crop_rev', 0):>6,.0f} | Planted: {info.get('planted_tiles', 0)} | Cows: {info.get('cows', 0)}")
