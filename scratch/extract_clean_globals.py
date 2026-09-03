import ast

with open(r"D:\kaggriculture\submission_rc1_ev_dispatcher.py", "r", encoding="utf-8") as f:
    code = f.read()

tree = ast.parse(code)

# Check all global variables assigned at module level
top_level_vars = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                top_level_vars.append(target.id)

print(f"Top-level global variables ({len(top_level_vars)}):")
for v in top_level_vars:
    print(f"  - {v}")
