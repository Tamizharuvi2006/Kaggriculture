import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

experts = challenger._V18_RUNTIME["experts"]
for name in experts.keys():
    actions = experts[name]["actions"]
    print(f"Expert `{name}`: {len(actions)} actions")
    if len(actions) < 700:
        print(f"  First 3: {actions[:3]}")
