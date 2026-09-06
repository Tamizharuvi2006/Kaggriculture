import os, sys, json

for rp, label in [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", "Match 1"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", "Match 14"),
]:
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 # hero is seat 0 in both
    # Count opponent animals over time
    opp_cows = [sum(1 for r in steps[s][opp_seat]["observation"]["farms"][opp_seat]["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "ANIMAL" and t.get("animal") == "COW") for s in range(0, len(steps), 24)]
    opp_sheep = [sum(1 for r in steps[s][opp_seat]["observation"]["farms"][opp_seat]["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "ANIMAL" and t.get("animal") == "SHEEP") for s in range(0, len(steps), 24)]
    opp_straw = [sum(1 for r in steps[s][opp_seat]["observation"]["farms"][opp_seat]["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY") for s in range(0, len(steps), 24)]
    print(f"\n--- {label} Opponent Profile ---")
    print("Opponent Cows by day:", opp_cows)
    print("Opponent Sheep by day:", opp_sheep)
    print("Opponent Strawberries by day:", opp_straw)
