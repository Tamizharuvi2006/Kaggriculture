import sys
import inspect
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208 as old_mod

funcs = [
    '_get',
    '_copy_action',
    '_v17_number',
    '_v18_state_features',
    '_v18_closed_loop_action',
    '_public_farm_counts',
    '_prioritize_capital_orders',
    '_adaptive_animal_focus',
    '_apply_fixed_board_adaptation',
    '_base_agent',
    'agent',
]

with open(r"D:\kaggriculture\scratch\extracted_funcs.py", "w", encoding="utf-8") as f:
    for name in funcs:
        fn = getattr(old_mod, name)
        src = inspect.getsource(fn)
        f.write(src + "\n\n")

print("Successfully extracted all active function sources to scratch/extracted_funcs.py")
