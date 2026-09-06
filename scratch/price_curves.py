import json

for match_idx, rp, label in [
    (1, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", "Match 1 (Loss)"),
    (2, r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", "Match 2 (Loss)"),
    (13, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\92603055\episode-92603055-replay.json", "Match 13 (Loss)"),
    (14, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", "Match 14 (Win $88k)"),
    (15, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95511283\episode-95511283-replay.json", "Match 15 (Win $79k)"),
    (18, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95702913\episode-95702913-replay.json", "Match 18 (Win $74k)"),
    (19, r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95773643\episode-95773643-replay.json", "Match 19 (Win $87k)"),
]:
    with open(rp, "r") as f: rep = json.load(f)
    steps = rep["steps"]
    milk_prices = [steps[d*24][0]["observation"]["market"]["prices"].get("MILK", 0) for d in range(11, 22)]
    straw_prices = [steps[d*24][0]["observation"]["market"]["prices"].get("STRAWBERRY", 0) for d in range(11, 22)]
    wool_prices = [steps[d*24][0]["observation"]["market"]["prices"].get("WOOL", 0) for d in range(11, 22)]
    print(f"\n{label}")
    print("Milk  D11-21:", milk_prices)
    print("Straw D11-21:", straw_prices)
    print("Wool  D11-21:", wool_prices)
