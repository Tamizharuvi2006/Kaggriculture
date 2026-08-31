import json

with open("D:/Kaggriculture/reports/exp122_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== EXP122: PER-EPISODE COMPARISON (Cluster 51 focus) ===")
for arm in data:
    print(f"\n--- {arm} ---")
    for t in data[arm]:
        if t.get("cluster") == 51:
            eid = t["episode_id"]
            r = t["terminal_reward"]
            sh = t["share"]
            won = "WIN" if t["won"] else "LOSS"
            stranded = t["stranded_crops"]
            d30 = t.get("strawberries", {}).get("D30", -1)
            print(f"  Ep {eid} Clust 51 | ${r:>9,.0f} | Share={sh:4.1f}% ({won}) | D30 Straw={d30} | Stranded={stranded}")

print("\n\n=== ARM-LEVEL SUMMARY ===")
import numpy as np
base_mean = np.mean([t["terminal_reward"] for t in data["A: D.1 Control"]])
for arm in data:
    trajs = data[arm]
    mr = np.mean([t["terminal_reward"] for t in trajs])
    delta = mr - base_mean
    wr = sum(1 for t in trajs if t["won"]) / len(trajs) * 100
    ms = np.mean([t["share"] for t in trajs])
    sc = np.mean([t["stranded_crops"] for t in trajs])
    ds = f"+${delta:,.0f}" if delta >= 0 else f"-${abs(delta):,.0f}"
    print(f"  {arm:<35s} | Mean=${mr:>9,.0f} | Delta={ds:>8s} | WR={wr:4.1f}% | Share={ms:5.1f}% | Stranded={sc:.1f}")

print("\n\n=== ARMS C vs D (is crop retirement adding anything on top of worker burst?) ===")
c_trajs = {t["episode_id"]: t for t in data["C: Late Worker Burst"]}
d_trajs = {t["episode_id"]: t for t in data["D: Combined Retirement+Burst"]}
diffs = 0
for eid in c_trajs:
    c_r = c_trajs[eid]["terminal_reward"]
    d_r = d_trajs[eid]["terminal_reward"]
    if abs(c_r - d_r) > 0.01:
        diffs += 1
        print(f"  Ep {eid}: C=${c_r:,.0f} D=${d_r:,.0f} diff={d_r-c_r:+,.0f}")
if diffs == 0:
    print("  C and D are IDENTICAL across all 20 episodes. Crop retirement adds nothing on top of worker burst.")

print("\n\n=== ARMS A vs B (is crop retirement doing anything at all?) ===")
a_trajs = {t["episode_id"]: t for t in data["A: D.1 Control"]}
b_trajs = {t["episode_id"]: t for t in data["B: Late Crop Retirement"]}
diffs = 0
for eid in a_trajs:
    a_r = a_trajs[eid]["terminal_reward"]
    b_r = b_trajs[eid]["terminal_reward"]
    if abs(a_r - b_r) > 0.01:
        diffs += 1
        print(f"  Ep {eid}: A=${a_r:,.0f} B=${b_r:,.0f} diff={b_r-a_r:+,.0f}")
if diffs == 0:
    print("  A and B are IDENTICAL across all 20 episodes. Crop retirement is a complete no-op.")
