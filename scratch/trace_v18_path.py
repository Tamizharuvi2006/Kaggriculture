import ast
import re

with open(r"D:\kaggriculture\submission_challenger_exp208.py", "r", encoding="utf-8") as f:
    code = f.read()

# Let's inspect `_base_agent` function code
match = re.search(r"def _base_agent\((.*?)\n(?=def |\Z)", code, re.DOTALL)
if match:
    print("Found _base_agent:")
    print(match.group(0)[:1500])

# Let's inspect `_v18_closed_loop_action`
match_v18 = re.search(r"def _v18_closed_loop_action\((.*?)\n(?=def |\Z)", code, re.DOTALL)
if match_v18:
    print("\nFound _v18_closed_loop_action:")
    print(match_v18.group(0)[:1500])
