import ast, sys

with open(r"D:\kaggriculture\economic_brain_v2\submission_adaptive_v4_1_ev_dispatcher.py", "r", encoding="utf-8") as f:
    orig_code = f.read()

with open(r"D:\kaggriculture\submission_v4_1_clean.py", "r", encoding="utf-8") as f:
    clean_code = f.read()

orig_tree = ast.parse(orig_code)
clean_tree = ast.parse(clean_code)

orig_funcs = {n.name: ast.dump(n) for n in orig_tree.body if isinstance(n, ast.FunctionDef)}
clean_funcs = {n.name: ast.dump(n) for n in clean_tree.body if isinstance(n, ast.FunctionDef)}

print(f"Orig functions: {len(orig_funcs)} | Clean functions: {len(clean_funcs)}")

# Check for differences in common functions
for name in clean_funcs:
    if name in orig_funcs:
        if clean_funcs[name] != orig_funcs[name]:
            print(f"DIFFERENCE IN FUNCTION: {name}")
    else:
        print(f"EXTRA FUNCTION IN CLEAN: {name}")

for name in orig_funcs:
    if name not in clean_funcs:
        # Check if it was supposed to be dead
        pass
