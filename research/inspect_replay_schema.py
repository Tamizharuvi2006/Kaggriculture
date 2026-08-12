import json
import os

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
fpath = os.path.join(PROJECT_ROOT, "l+reviews", "91272656.json")
with open(fpath, "r", encoding="utf-8") as f:
    d = json.load(f)

step100 = d["steps"][100]
print("Observation keys:", step100[0]["observation"].keys())
farms = step100[0]["observation"].get("farms", [])
print("Farm 0 keys:", farms[0].keys() if farms else None)
if farms:
    print("Crops sample:", farms[0].get("crops")[:3] if farms[0].get("crops") else None)
    print("Animals sample:", farms[0].get("animals")[:3] if farms[0].get("animals") else None)
    print("Farmer:", farms[0].get("farmer"))
    print("Hands:", farms[0].get("hands"))
