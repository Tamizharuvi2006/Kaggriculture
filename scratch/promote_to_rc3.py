import shutil, hashlib

src = r"D:\kaggriculture\submission_h6_threshold16.py"
dst = r"D:\kaggriculture\submission_rc3_h6.py"

shutil.copyfile(src, dst)

with open(dst, "rb") as f:
    sha = hashlib.sha256(f.read()).hexdigest()

print(f"Created submission_rc3_h6.py successfully!")
print(f"SHA256: {sha}")
