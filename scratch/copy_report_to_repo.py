import shutil

src = r"C:\Users\aruvi\.gemini\antigravity-cli\brain\5f3761dd-1db1-44b4-ad11-5a87c1e9c4d3\PHASE11_RC3_LABORATORY_BASELINE_REPORT.md"
dst = r"D:\kaggriculture\reports\PHASE11_RC3_LABORATORY_BASELINE_REPORT.md"

shutil.copyfile(src, dst)
print("Copied milestone report to repository reports/ directory!")
