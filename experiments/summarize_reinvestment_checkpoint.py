import json
import statistics

with open(r"D:\kaggriculture\day12_reinvestment_checkpoint.json", "r") as f:
    data = json.load(f)

print("=" * 80)
print(" DAY-12 REINVESTMENT CHECKPOINT SUMMARY STATUS")
print("=" * 80)

names = {
    "C1": "Control (10 Melons + 8 Cows)",
    "C2": "Conditional Cow 9-10 Expansion",
    "C3": "Day-12 SW/SE Land Unlock",
    "C4": "Day 12-20 Strawberry Crops",
    "C5": "Combined Smart Reinvestment",
}

for var in ["C1", "C2", "C3", "C4", "C5"]:
    if var in data:
        matches = list(data[var].values())
        count = len(matches)
        if count > 0:
            d8 = statistics.mean([m["d8_cash"] for m in matches])
            d15 = statistics.mean([m["d15_cash"] for m in matches])
            final = statistics.mean([m["final_cash"] for m in matches])
            v41 = statistics.mean([m["final_v41"] for m in matches])
            wins = sum(1 for m in matches if m["win"])
            win_rate = (wins / count) * 100.0
            print(f" {var} ({names[var]:<30}) | Completed: {count:>3}/100 | Day-15: ${d15:,.2f} | Final: ${final:,.2f} | Win Rate: {win_rate:.1f}%")
        else:
            print(f" {var} ({names[var]:<30}) | Completed: 0/100")
    else:
        print(f" {var} ({names[var]:<30}) | Completed: 0/100")

print("=" * 80)
