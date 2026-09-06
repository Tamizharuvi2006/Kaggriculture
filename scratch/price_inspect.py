import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14 (Ceiling Win)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1 (Crash)"),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1, "Match 2 (Crash)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95622859\episode-95622859-replay.json", 0, "Match 17 (Floor Collapse)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95775674\episode-95775674-replay.json", 0, "Match 20 (Floor Collapse)"),
]

for rp, hero_seat, label in replays:
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    # Look at Day 11 step (around 264)
    obs = steps[264][hero_seat]["observation"]
    prices = obs["market"]["prices"]
    opp_seat = 1 - hero_seat
    opp_obs = steps[264][opp_seat]["observation"]
    print(f"\n--- {label} (Day 11) ---")
    print(f"Prices: MILK={prices.get('MILK')} | WOOL={prices.get('WOOL')} | STRAWBERRY={prices.get('STRAWBERRY')} | MELON={prices.get('MELON')} | WHEAT={prices.get('WHEAT')}")
    # Also look at Day 20 prices
    obs20 = steps[480][hero_seat]["observation"]
    prices20 = obs20["market"]["prices"]
    print(f"Prices D20: MILK={prices20.get('MILK')} | WOOL={prices20.get('WOOL')} | STRAWBERRY={prices20.get('STRAWBERRY')} | MELON={prices20.get('MELON')} | WHEAT={prices20.get('WHEAT')}")
