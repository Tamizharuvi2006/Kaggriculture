import hashlib

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

old_path = r"D:\kaggriculture\submission_challenger_exp208.py"
new_path = r"D:\kaggriculture\submission_challenger_exp208_clean.py"

with open(old_path, "r", encoding="utf-8") as f:
    old_lines = len(f.read().splitlines())
with open(new_path, "r", encoding="utf-8") as f:
    new_lines = len(f.read().splitlines())

print("OLD FILE:")
print(f"  Path: {old_path}")
print(f"  Lines: {old_lines}")
print(f"  SHA-256: {sha256_file(old_path)}")

print("\nNEW CLEAN FILE:")
print(f"  Path: {new_path}")
print(f"  Lines: {new_lines}")
print(f"  SHA-256: {sha256_file(new_path)}")
