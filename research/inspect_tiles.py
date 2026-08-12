import json
import os

PROJECT_ROOT = r"D:\kagriulture\Kaggriculture"
fpath = os.path.join(PROJECT_ROOT, "l+reviews", "91272656.json")
with open(fpath, "r", encoding="utf-8") as f:
    d = json.load(f)

step100 = d["steps"][100]
farms = step100[0]["observation"].get("farms", [])
tiles = farms[0].get("tiles", [])
print("Tiles count:", len(tiles))
for i, t in enumerate(tiles[:5]):
    print(f"Tile {i}: {t}")
