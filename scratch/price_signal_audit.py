import os, sys, json
import kaggle_environments

SELECTED_REPLAYS = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json", 1),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91296662\episode-91296662-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91297572\episode-91297572-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91341377\episode-91341377-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91694495\episode-91694495-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\92602112\episode-92602112-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\92603055\episode-92603055-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95511283\episode-95511283-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95579586\episode-95579586-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95622859\episode-95622859-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95702913\episode-95702913-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95773643\episode-95773643-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95775674\episode-95775674-replay.json", 0),
]

# Known deltas: RC6_D1 - RC12
deltas = [-17909, -18238, +1004, -5723, +8895, +11303, +8498, +1791, -9082, +6060, +3522, +9485, -17206, +14920, +16553, +7064, -20273, +6656, +7880, -11928]

for i, (rp, hero_seat) in enumerate(SELECTED_REPLAYS):
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    p_d9 = steps[9*24][hero_seat]["observation"]["market"]["prices"]
    p_d10 = steps[10*24][hero_seat]["observation"]["market"]["prices"]
    p_d11 = steps[11*24][hero_seat]["observation"]["market"]["prices"]
    p_d12 = steps[12*24][hero_seat]["observation"]["market"]["prices"]
    
    milk_d9 = p_d9.get("MILK", 0)
    milk_d11 = p_d11.get("MILK", 0)
    milk_trend = milk_d11 - milk_d9
    
    wool_d11 = p_d11.get("WOOL", 0)
    straw_d11 = p_d11.get("STRAWBERRY", 0)
    
    status = "WIN " if deltas[i] > 1000 else ("LOSS" if deltas[i] < -1000 else "TIE ")
    print(f"#{i+1:02d} | Delta: {deltas[i]:>+7,d} [{status}] | Milk D9:{milk_d9:>3} D11:{milk_d11:>3} Tr:{milk_trend:>+3} | Wool D11:{wool_d11:>3} | Straw D11:{straw_d11:>3}")
