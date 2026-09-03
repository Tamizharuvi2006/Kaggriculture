import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208 as old_mod

print("_V18_RUNTIME keys:", list(old_mod._V18_RUNTIME.keys()))
for k in old_mod._V18_RUNTIME.keys():
    v = old_mod._V18_RUNTIME[k]
    if isinstance(v, dict):
        print(f"  {k}: dict with keys {list(v.keys())}")
    else:
        print(f"  {k}: {type(v).__name__} = {v if not isinstance(v, (list, str)) or len(str(v)) < 50 else str(v)[:50]}")
