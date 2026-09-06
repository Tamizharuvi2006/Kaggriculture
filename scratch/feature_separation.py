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

deltas = [-17909, -18238, +1004, -5723, +8895, +11303, +8498, +1791, -9082, +6060, +3522, +9485, -17206, +14920, +16553, +7064, -20273, +6656, +7880, -11928]

for i, (rp, hero_seat) in enumerate(SELECTED_REPLAYS):
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    
    # State at end of day 10 (step 263)
    s263 = steps[263][hero_seat]["observation"]
    s264 = steps[264][hero_seat]["observation"] # start of day 11
    
    farm = s264["farms"][hero_seat]
    shed = s264["private"]["shed"]
    prices = s264["market"]["prices"]
    
    # Check melons in shed at start of day 11 (ready to be sold!)
    melons_ready = shed.get("MELON", 0)
    p_melon = prices.get("MELON", 0)
    melon_windfall = melons_ready * p_melon * 0.95
    
    # Check animals at start of day 11
    cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    sheep = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    curr_herd = cows + sheep
    
    # Opponent cash at day 11
    opp_seat = 1 - hero_seat
    opp_cash = steps[264][opp_seat]["observation"]["farms"][opp_seat]["money"]
    
    status = "WIN " if deltas[i] > 1000 else ("LOSS" if deltas[i] < -1000 else "TIE ")
    print(f"#{i+1:02d} | Delta: {deltas[i]:>+7,d} [{status}] | Herd D11: {curr_herd} ({cows}c,{sheep}s) | Melons: {melons_ready:>2d} (${melon_windfall:>6,.0f}) | P_Milk:{prices.get('MILK'):>3} P_Straw:{prices.get('STRAWBERRY'):>3} | OppCash: ${opp_cash:>6,.0f}")
