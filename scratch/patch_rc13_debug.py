with open(r"D:\kaggriculture\submission_rc13.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "except Exception as e:" in l:
        lines[i] = "    except Exception as e:\n        import traceback; traceback.print_exc()\n"

with open(r"D:\kaggriculture\submission_rc13.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
