import hashlib
import os

fpath = r"D:\kaggriculture\submission_challenger_exp208_clean.py"
with open(fpath, "rb") as f:
    data = f.read()

sha = hashlib.sha256(data).hexdigest()
size = len(data)
lines = len(data.splitlines())

print("=========================================================================================")
print("     FINAL PRODUCTION CANDIDATE INTEGRITY AUDIT                                          ")
print("=========================================================================================")
print(f"File Path    : {fpath}")
print(f"Total Lines  : {lines:,}")
print(f"Total Bytes  : {size:,}")
print(f"SHA-256 Hash : {sha}")
