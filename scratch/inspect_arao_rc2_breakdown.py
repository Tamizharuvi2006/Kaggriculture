import json

path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(path_arao) as f: rep_arao = json.load(f)
steps = rep_arao["steps"]

# Our bot is Seat 1
print("=" * 80)
print("ARAO SEAT 1 REPLAY INSPECTION:")
print("=" * 80)

# Check our final assets
last_step = steps[-1]
f1 = last_step[1]["observation"]["farms"][1]
print("Final Money:", f1["money"])
print("Final Cows:", sum(1 for r in f1["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "COW"))
print("Final Sheep:", sum(1 for r in f1["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP"))

# Check when the market saturated in Arao
for s_idx in range(len(steps)-1):
    obs = steps[s_idx][1]["observation"]
    inv_straw = obs["market"]["inventory"].get("STRAWBERRY", 0)
    p_straw = obs["market"]["prices"].get("STRAWBERRY", 0)
    if inv_straw >= 10000:
        print(f"Arao Market Saturated at Day {s_idx // 24} Hour {s_idx % 24} (Inv: {inv_straw}, Price: ${p_straw:.1f})")
        break
