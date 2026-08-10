import json
import statistics

with open(r"D:\kaggriculture\low_melon_curve_checkpoint.json", "r") as f:
    data = json.load(f)

print("=" * 80)
print(" LOW-MELON CHECKPOINT SUMMARY STATUS")
print("=" * 80)

for cnt in ["7", "8", "9", "10"]:
    if cnt in data:
        matches = list(data[cnt].values())
        count = len(matches)
        if count > 0:
            d8 = statistics.mean([m["d8_cash"] for m in matches])
            d15 = statistics.mean([m["d15_cash"] for m in matches])
            final = statistics.mean([m["final_cash"] for m in matches])
            v41 = statistics.mean([m["final_v41"] for m in matches])
            wins = sum(1 for m in matches if m["win"])
            win_rate = (wins / count) * 100.0
            print(f" {cnt:>2} Melons | Completed: {count:>3}/200 | Day-8: ${d8:,.2f} | Day-15: ${d15:,.2f} | Final: ${final:,.2f} | Win Rate: {win_rate:.1f}%")
        else:
            print(f" {cnt:>2} Melons | Completed: 0/200")
    else:
        print(f" {cnt:>2} Melons | Completed: 0/200")

print("=" * 80)
