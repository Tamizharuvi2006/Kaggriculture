import json

with open("D:/Kaggriculture/reports/exp121_step_level_divergence_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for ep in data:
    if ep["cluster"] != 51:
        continue
    eid = ep["episode_id"]
    seat = ep["elite_seat"]
    el_rew = ep["elite_terminal_reward"]
    d1_rew = ep["d1_terminal_reward"]
    delta = el_rew - d1_rew
    winner = "ELITE_WINS" if el_rew > d1_rew else "D1_WINS"
    print(f"=== Ep {eid} Cluster 51 Seat {seat} | Elite ${el_rew:,.0f} D1 ${d1_rew:,.0f} Delta {delta:+,.0f} {winner} ===")
    ms = ep.get("milestone_snapshots", {})
    for day_label in ["D2", "D4", "D6", "D11", "D16", "D21", "D26", "D30"]:
        if day_label in ms:
            d1 = ms[day_label]["d1"]
            el = ms[day_label]["elite"]
            d1m = d1["money"]
            elm = el["money"]
            print(f"  {day_label}: D1 money={d1m:,.0f} hands={d1['hands']} cows={d1['cows']} straw={d1['strawberries']} | Elite money={elm:,.0f} hands={el['hands']} cows={el['cows']} straw={el['strawberries']}")
    print()

print("=== DIVERGENCE CATEGORIES (all episodes) ===")
from collections import Counter
cats = Counter()
for ep in data:
    fa = ep.get("first_action_divergence")
    if fa:
        cats[fa["category"]] += 1
for cat, cnt in cats.most_common():
    print(f"  {cat}: {cnt}")

print()
print("=== CLUSTER 51 DIVERGENCE BY DAY ===")
for ep in data:
    if ep["cluster"] != 51:
        continue
    eid = ep["episode_id"]
    divs = ep.get("divergences_by_day", {})
    total = sum(divs.values())
    print(f"  Ep {eid}: {total} total divergences")
    for day, cnt in sorted(divs.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"    {day}: {cnt}")

print()
print("=== ALL EPISODES SUMMARY ===")
d1_wins = sum(1 for ep in data if ep["d1_terminal_reward"] > ep["elite_terminal_reward"])
elite_wins = sum(1 for ep in data if ep["elite_terminal_reward"] > ep["d1_terminal_reward"])
ties = len(data) - d1_wins - elite_wins
print(f"D1 wins: {d1_wins}/20, Elite wins: {elite_wins}/20, Ties: {ties}/20")

print()
print("=== ELITE WIN CASES DETAIL ===")
for ep in data:
    el = ep["elite_terminal_reward"]
    d1 = ep["d1_terminal_reward"]
    if el > d1:
        eid = ep["episode_id"]
        clust = ep["cluster"]
        seat = ep["elite_seat"]
        delta = el - d1
        print(f"  Ep {eid} Clust {clust} Seat {seat} | Elite ${el:,.0f} D1 ${d1:,.0f} Delta +{delta:,.0f}")
        ms = ep.get("milestone_snapshots", {})
        for day_label in ["D21", "D26", "D30"]:
            if day_label in ms:
                d1s = ms[day_label]["d1"]
                els = ms[day_label]["elite"]
                print(f"    {day_label}: D1 straw={d1s['strawberries']} hands={d1s['hands']} money={d1s['money']:,.0f} | Elite straw={els['strawberries']} hands={els['hands']} money={els['money']:,.0f}")
