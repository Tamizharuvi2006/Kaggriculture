with open(r"D:\kaggriculture\submission_rc4_2_hybrid.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "return day >= 4" in line and i > 580 and i < 600:
        lines[i] = "        return True\n"
        print(f"Replaced line {i+1}: {line.strip()} -> return True")
        break

with open(r"D:\kaggriculture\submission_rc5_a_early_pasture.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Created D:\\kaggriculture\\submission_rc5_a_early_pasture.py successfully!")
