import ast
import re

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

def get_referenced_names(node):
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names

# Active runtime entry functions for v18:
# `agent` -> calls `_base_agent`
# `_base_agent` with v18 uses:
#   `_V18_RUNTIME`, `_v18_closed_loop_action`, `_copy_action`, `_apply_fixed_board_adaptation`, `_get`
# Let's trace reachable functions starting strictly from:
#   ['agent', '_base_agent', '_v18_closed_loop_action', '_apply_fixed_board_adaptation']

visited_defs = set()
visited_assigns = set()
queue = ['agent', '_base_agent', '_v18_closed_loop_action', '_apply_fixed_board_adaptation']

while queue:
    curr = queue.pop(0)
    if curr in visited_defs:
        continue
    visited_defs.add(curr)
    node = top_level_defs.get(curr)
    if node:
        refs = get_referenced_names(node)
        for ref in refs:
            # Avoid pulling in other version functions from the if/elif ladder of _base_agent
            if ref in {'_v15_senkin_action', '_v14_senkin_action', '_v13_senkin_action', '_v16_senkin_action',
                        '_v17_learned_action', '_v12_syouya_action', '_v11_radiant_schedule', '_v16_core_schedule',
                        '_apply_market_interference', '_observe_opponent', '_assign_actions', '_market_orders'}:
                continue
            if ref in top_level_defs and ref not in visited_defs:
                queue.append(ref)
            if ref in top_level_assigns:
                visited_assigns.add(ref)

# Also check references from visited assigns
assign_queue = list(visited_assigns)
while assign_queue:
    curr = assign_queue.pop(0)
    # Don't pull in dead schedule variables
    if curr in {'_FIXED_SCHEDULE_B85', '_V10_SCHEDULE_B85', '_V11_RADIANT_SCHEDULE_B85', 
                '_V11_RADIANT_ALPHA_SCHEDULE_B85', '_V12_SYOUYA_SCHEDULE_B85', '_V13_SENKIN_SCHEDULE_B85',
                '_V16_P0_SCHEDULE_B85', '_V16_P1_SCHEDULE_B85', '_V17_SCHEDULE_B85', '_V17_MARKET_MODEL_B85',
                '_FIXED_SCHEDULE', '_V10_SCHEDULE', '_V11_RADIANT_SCHEDULE', '_V11_RADIANT_ALPHA_SCHEDULE',
                '_V12_SYOUYA_SCHEDULE', '_V13_SENKIN_SCHEDULE', '_V16_P0_SCHEDULE', '_V16_P1_SCHEDULE',
                '_V17_SCHEDULE', '_V17_MARKET_MODEL'}:
        continue
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

print(f"Reachable functions for v18 ({len(visited_defs)}): {sorted(list(visited_defs))}")
print(f"Reachable variables for v18 ({len(visited_assigns)}): {sorted(list(visited_assigns))}")

# Check sizes of dead base85 blobs:
dead_blobs = ['_FIXED_SCHEDULE_B85', '_V10_SCHEDULE_B85', '_V11_RADIANT_SCHEDULE_B85', 
              '_V11_RADIANT_ALPHA_SCHEDULE_B85', '_V12_SYOUYA_SCHEDULE_B85', '_V13_SENKIN_SCHEDULE_B85',
              '_V16_P0_SCHEDULE_B85', '_V16_P1_SCHEDULE_B85', '_V17_SCHEDULE_B85', '_V17_MARKET_MODEL_B85']

for blob in dead_blobs:
    node = top_level_assigns.get(blob)
    if node:
        print(f"Dead blob {blob}: lines {node.lineno} to {node.end_lineno}")
