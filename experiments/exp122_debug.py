import json

with open("D:/Kaggriculture/reports/exp122_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Check per-episode deltas for C vs A
print("=== PER-EPISODE DELTA: Arm C (Worker Burst) vs Arm A (Control) ===")
a_trajs = {t["episode_id"]: t for t in data["A: D.1 Control"]}
c_trajs = {t["episode_id"]: t for t in data["C: Late Worker Burst"]}

deltas = []
for eid in sorted(a_trajs.keys()):
    a_r = a_trajs[eid]["terminal_reward"]
    c_r = c_trajs[eid]["terminal_reward"]
    d = c_r - a_r
    deltas.append(d)
    clust = a_trajs[eid]["cluster"]
    print(f"  Ep {eid} Clust {clust} | A=${a_r:>9,.0f} C=${c_r:>9,.0f} | Delta=${d:+,.0f}")

import numpy as np
print(f"\n  Mean delta: ${np.mean(deltas):+,.0f}")
print(f"  Median delta: ${np.median(deltas):+,.0f}")
print(f"  Positive deltas: {sum(1 for d in deltas if d > 0)}/{len(deltas)}")
print(f"  Zero deltas: {sum(1 for d in deltas if abs(d) < 0.01)}/{len(deltas)}")
print(f"  Negative deltas: {sum(1 for d in deltas if d < 0)}/{len(deltas)}")

# Check if the crop retirement doomed_tiles was ever populated
print("\n\n=== CROP RETIREMENT DEBUG ===")
b_trajs = {t["episode_id"]: t for t in data["B: Late Crop Retirement"]}
d_trajs = {t["episode_id"]: t for t in data["D: Combined Retirement+Burst"]}
for eid in sorted(b_trajs.keys()):
    b = b_trajs[eid]
    d = d_trajs[eid]
    b_doomed = b.get("doomed", {})
    d_doomed = d.get("doomed", {})
    if b_doomed or d_doomed:
        print(f"  Ep {eid}: B doomed={b_doomed} D doomed={d_doomed}")
    else:
        pass  # no doomed data recorded

# Check if any doomed data exists at all
all_doomed = []
for arm in data:
    for t in data[arm]:
        doomed = t.get("doomed", {})
        if doomed:
            all_doomed.append((arm, t["episode_id"], doomed))

if not all_doomed:
    print("  NO doomed tile data was recorded in ANY episode across ANY arm.")
    print("  This confirms: the crop retirement logic never found any doomed tiles.")
    print("  D.1 stops planting at Day 18, so no crops are truly doomed (can't mature before terminal).")
else:
    print(f"  Found {len(all_doomed)} episodes with doomed tile data:")
    for arm, eid, doomed in all_doomed:
        print(f"    {arm} Ep {eid}: {doomed}")
