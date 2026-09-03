import ast

with open(r"D:\kaggriculture\submission_challenger_exp208.py", "r", encoding="utf-8") as f:
    code = f.read()

tree = ast.parse(code)

top_level_defs = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
top_level_assigns = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                top_level_assigns[target.id] = node

def get_calls(func_name):
    node = top_level_defs[func_name]
    calls = set()
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            calls.add(child.func.id)
        if isinstance(child, ast.Name):
            names.add(child.id)
    return calls, names

# Check all functions in visited_defs
v18_funcs = ['agent', '_base_agent', '_v18_closed_loop_action', '_apply_fixed_board_adaptation',
             '_copy_action', '_get', '_v18_state_features', '_v17_number',
             '_public_farm_counts', '_prioritize_capital_orders', '_adaptive_animal_focus']

for f in v18_funcs:
    calls, names = get_calls(f)
    print(f"\nFunction `{f}` calls: {calls}")
    print(f"  global names referenced: {[n for n in names if n in top_level_assigns or n in top_level_defs]}")
