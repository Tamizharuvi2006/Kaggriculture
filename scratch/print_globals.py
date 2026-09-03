import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208 as old_mod

for k in dir(old_mod):
    if k.startswith("_V") or k.startswith("_F"):
        v = getattr(old_mod, k)
        t = type(v).__name__
        l = len(v) if hasattr(v, "__len__") else "N/A"
        print(f"  {k} ({t}, len={l})")
