import ast, sys

with open(r"D:\kaggriculture\submission_rc1_ev_dispatcher.py", "r", encoding="utf-8") as f:
    code = f.read()

tree = ast.parse(code)

# Find all top-level functions and classes
func_defs = {}
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        func_defs[node.name] = node

print(f"Total top-level functions defined in file: {len(func_defs)}")

# Trace call graph starting from `agent`
visited = set()
to_visit = ["agent"]

while to_visit:
    curr = to_visit.pop(0)
    if curr in visited or curr not in func_defs:
        continue
    visited.add(curr)
    
    # Find all function calls inside `curr`
    for node in ast.walk(func_defs[curr]):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            callee = node.func.id
            if callee in func_defs and callee not in visited and callee not in to_visit:
                to_visit.append(callee)

print(f"Functions reachable from agent(): {len(visited)}")
print("\nReachable functions:")
for f in sorted(visited):
    print(f"  + {f}")

unreachable = set(func_defs.keys()) - visited
print(f"\nDEAD / UNREACHABLE functions ({len(unreachable)}):")
for f in sorted(unreachable):
    print(f"  - {f}")
