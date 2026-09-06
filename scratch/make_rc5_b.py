with open(r"D:\kaggriculture\submission_rc5_a_early_pasture.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'tasks.append(_task(prio, pos, ["BUILD_PASTURE"], None, "build", ev))' in line:
        # Check indentation and replace
        indent = " " * 12
        new_lines = [
            f"{indent}# RC5-B Labor Protection: Defer speculative empty pasture building to afternoon (Hour >= 14)\n",
            f"{indent}# during opening days (Days 0-3) unless an animal is physically waiting.\n",
            f"{indent}if waiting or day >= 4 or hour >= 14:\n",
            f"{indent}    tasks.append(_task(prio, pos, [\"BUILD_PASTURE\"], None, \"build\", ev))\n"
        ]
        lines[i:i+1] = new_lines
        print(f"Replaced line {i+1} with labor-protected pasture generation.")
        break

with open(r"D:\kaggriculture\submission_rc5_b_labor_protected.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Created D:\\kaggriculture\\submission_rc5_b_labor_protected.py successfully!")
