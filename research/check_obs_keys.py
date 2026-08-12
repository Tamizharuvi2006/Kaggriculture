import json
import glob
import os

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
fpath = glob.glob(os.path.join(PROJECT_ROOT, "l+reviews", "*.json"))[0]
with open(fpath, "r", encoding="utf-8") as f:
    data = json.load(f)

step = data["steps"][24][0]
obs = step["observation"]
print("Obs keys:", obs.keys())
if "market" in obs:
    print("Market:", obs["market"])
if "town" in obs:
    print("Town:", obs["town"])
if "prices" in obs:
    print("Prices:", obs["prices"])
