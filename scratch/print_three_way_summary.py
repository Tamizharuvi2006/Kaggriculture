import json, numpy as np

with open("reports/RC4_THREE_WAY_PAIRED_AUDIT.json") as f:
    d = json.load(f)

print("=" * 75)
print(f"{'AGENT':<6} | {'MEAN SCORE':>12} | {'FLOOR':>10} | {'CEILING':>10} | {'STRAW REV':>11} | {'OTHER REV':>11}")
print("-" * 75)

for agent in ("RC2", "RC3", "RC4"):
    s_rev = np.mean(d[agent]["straw_rev"])
    o_rev = np.mean(d[agent]["other_rev"])
    score = np.mean(d[agent]["scores"])
    floor = np.min(d[agent]["scores"])
    ceil = np.max(d[agent]["scores"])
    print(f"{agent:<6} | ${score:>11,.0f} | ${floor:>9,.0f} | ${ceil:>9,.0f} | ${s_rev:>10,.0f} | ${o_rev:>10,.0f}")

print("=" * 75)
