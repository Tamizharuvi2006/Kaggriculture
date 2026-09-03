import ast
import os
import sys

with open(r"D:\kaggriculture\submission_challenger_exp208.py", "r", encoding="utf-8") as f:
    code = f.read()

tree = ast.parse(code)

top_level_defs = {}
top_level_assigns = {}

for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        top_level_defs[node.name] = node
    elif isinstance(node, ast.ClassDef):
        top_level_defs[node.name] = node
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                top_level_assigns[target.id] = node

print(f"Total top-level functions/classes: {len(top_level_defs)}")
print(f"Total top-level assignments: {len(top_level_assigns)}")

# Find all Name nodes inside a function/class AST
def get_referenced_names(node):
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names

# Breadth-first search from `agent`
visited_defs = set()
visited_assigns = set()
queue = ["agent"]

while queue:
    curr = queue.pop(0)
    if curr in visited_defs:
        continue
    visited_defs.add(curr)
    
    node = top_level_defs.get(curr)
    if node:
        refs = get_referenced_names(node)
        for ref in refs:
            if ref in top_level_defs and ref not in visited_defs:
                queue.append(ref)
            if ref in top_level_assigns:
                visited_assigns.add(ref)

# Also check references from visited assigns
assign_queue = list(visited_assigns)
while assign_queue:
    curr = assign_queue.pop(0)
    node = top_level_assigns.get(curr)
    if node:
        refs = get_referenced_names(node)
        for ref in refs:
            if ref in top_level_defs and ref not in visited_defs:
                visited_defs.add(ref)
                queue.append(ref)
            if ref in top_level_assigns and ref not in visited_assigns:
                visited_assigns.add(ref)
                assign_queue.append(ref)

print("\n--- REACHABLE FROM `agent` ---")
print(f"Reachable functions/classes ({len(visited_defs)}): {sorted(list(visited_defs))}")
print(f"Reachable variables ({len(visited_assigns)}): {sorted(list(visited_assigns))}")

print("\n--- UNREACHABLE TOP-LEVEL DEFINITIONS ---")
unreachable_defs = set(top_level_defs.keys()) - visited_defs
print(f"Unreachable functions/classes ({len(unreachable_defs)}): {sorted(list(unreachable_defs))}")

print("\n--- UNREACHABLE TOP-LEVEL ASSIGNMENTS ---")
unreachable_assigns = set(top_level_assigns.keys()) - visited_assigns
print(f"Unreachable variables ({len(unreachable_assigns)}): {sorted(list(unreachable_assigns))}")
