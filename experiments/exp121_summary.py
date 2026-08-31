import json

with open("D:/Kaggriculture/reports/exp121_step_level_divergence_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== ALL 20 EPISODES: D1 vs ELITE ===")
header = "{:>10} {:>5} {:>4} {:>10} {:>10} {:>10} {:>10} {:>8} {:>8} {:>8} {:>8}".format(
    "EpID", "Clust", "Seat", "Elite$", "D1$", "Delta", "Winner", "D21str", "D26str", "D30str", "D30hand")
print(header)
for ep in data:
    eid = ep["episode_id"]
    clust = ep["cluster"]
    seat = ep["elite_seat"]
    el = ep["elite_terminal_reward"]
    d1 = ep["d1_terminal_reward"]
    delta = el - d1
    winner = "ELITE" if el > d1 else "D1"
    ms = ep.get("milestone_snapshots", {})
    d21s = ms.get("D21", {}).get("d1", {}).get("strawberries", -1)
    d26s = ms.get("D26", {}).get("d1", {}).get("strawberries", -1)
    d30s = ms.get("D30", {}).get("d1", {}).get("strawberries", -1)
    d30h = ms.get("D30", {}).get("d1", {}).get("hands", -1)
    row = "{:>10} {:>5} {:>4} {:>10,.0f} {:>10,.0f} {:>+10,.0f} {:>10} {:>8} {:>8} {:>8} {:>8}".format(
        eid, clust, seat, el, d1, delta, winner, d21s, d26s, d30s, d30h)
    print(row)

print()
print("=== ELITE WIN CASES: Elite late-game detail ===")
for ep in data:
    el = ep["elite_terminal_reward"]
    d1 = ep["d1_terminal_reward"]
    if el > d1:
        eid = ep["episode_id"]
        clust = ep["cluster"]
        ms = ep.get("milestone_snapshots", {})
        print("Ep {} Clust {}:".format(eid, clust))
        for dl in ["D21", "D26", "D30"]:
            if dl in ms:
                e = ms[dl]["elite"]
                d = ms[dl]["d1"]
                print("  {}: D1 straw={} hands={} cows={} money={:,.0f} | ELITE straw={} hands={} cows={} money={:,.0f}".format(
                    dl, d["strawberries"], d["hands"], d["cows"], d["money"],
                    e["strawberries"], e["hands"], e["cows"], e["money"]))
        print()

# Also show D1 hands=0 throughout - interesting!
print("=== D1 HANDS PATTERN (all episodes) ===")
for ep in data:
    ms = ep.get("milestone_snapshots", {})
    hands_by_day = []
    for dl in ["D2", "D4", "D6", "D11", "D16", "D21", "D26", "D30"]:
        if dl in ms:
            hands_by_day.append("{}:{}".format(dl, ms[dl]["d1"]["hands"]))
    eid = ep["episode_id"]
    print("  Ep {}: {}".format(eid, " ".join(hands_by_day)))
