import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208 as old_mod

print("DEFAULT_STRATEGY['fixed_schedule_version'] =", old_mod.DEFAULT_STRATEGY.get("fixed_schedule_version"))
print("DEFAULT_STRATEGY['use_fixed_schedule'] =", old_mod.DEFAULT_STRATEGY.get("use_fixed_schedule"))

for k, v in old_mod.DEFAULT_STRATEGY.items():
    if "schedule" in k or "version" in k:
        print(f"  {k}: {v}")
