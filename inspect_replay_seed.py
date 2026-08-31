import json
import subprocess

# Seed of episode 91697084
# In episode 91697084 replay:
with open("D:/kaggriculture/reports/step5b/old_loss_gauntlet/raw_replays/91697084/episode-91697084-replay.json") as f:
    rep = json.load(f)

p0_name = rep.get("info", {}).get("TeamNames", ["P0", "P1"])[0]
print("Replay info:", rep.get("info"))
print("Initial configuration:", rep.get("configuration"))
