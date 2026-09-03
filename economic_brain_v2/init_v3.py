import sys
sys.path.insert(0, r"D:\kaggriculture")

import shutil, os

src = r"D:\kaggriculture\economic_brain_v2\submission_adaptive_v2_economic.py"
dst = r"D:\kaggriculture\economic_brain_v2\submission_adaptive_v3_economic.py"

with open(src, "r", encoding="utf-8") as f:
    code = f.read()

# Update version / docstring
code = code.replace("Adaptive V2 Economic Agent", "Adaptive V3 Economic Brain")

with open(dst, "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_adaptive_v3_economic.py successfully!")
