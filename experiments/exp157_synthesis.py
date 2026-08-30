"""EXP157 Synthesis & Regime Analysis Script."""
import os
import json
import numpy as np

REPORTS_DIR = r"D:\kaggriculture\reports"
res_file = os.path.join(REPORTS_DIR, "exp157_policy_architecture_results.json")

with open(res_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Aggregate events across all matches
all_events = []
for entry in data:
    for ev in entry["events"]:
        ev["bot_key"] = entry["bot_key"]
        ev["tier"] = entry["tier"]
        all_events.append(ev)

regimes = set(e["regime"] for e in all_events)
print("=" * 100)
print(f"EXP157 SYNTHESIS: {len(all_events)} STATE-ACTION TRANSITIONS ANALYZED")
print("=" * 100)

for r in sorted(regimes):
    sub = [e for e in all_events if e["regime"] == r]
    diffs = [e for e in sub if e["diff"]]
    pct_diff = (len(diffs) / len(sub)) * 100 if sub else 0
    earliest_step = min(e["step"] for e in sub) if sub else -1
    print(f"\nREGIME: {r}")
    print(f"  Total Observations: {len(sub)} | Divergent Actions vs D.1: {len(diffs)} ({pct_diff:.1f}%)")
    print(f"  Earliest Trigger Step: {earliest_step} (Day {earliest_step // 24})")
    
    # Inspect sample action differences
    if diffs:
        sample = diffs[0]
        print(f"  Sample Divergence at Step {sample['step']} vs {sample['bot_key']}:")
        print(f"    D.1 Orders : {sample['h_orders']}")
        print(f"    Opp Orders : {sample['o_orders']}")

print("\n" + "=" * 100)
