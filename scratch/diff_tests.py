with open(r"D:\kaggriculture\scratch\test_fixed_step_vs_arao.py") as f1, open(r"D:\kaggriculture\scratch\test_step_populated.py") as f2:
    lines1 = f1.readlines()
    lines2 = f2.readlines()

print("test_fixed_step_vs_arao.py has", len(lines1), "lines")
print("test_step_populated.py has", len(lines2), "lines")
