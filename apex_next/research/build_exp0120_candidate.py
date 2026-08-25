"""
Build Candidate Submission for EXP-0120 (CAND-120-05 Tri-Crop)
Applies:
- DEFAULT_STRATEGY["strawberries"] = 24 (down from 34)
- DEFAULT_STRATEGY["opening_melons"] = 14 (up from 9)
- base_profile["tomatoes"] = 6 (up from 0)
"""
import os
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.path.join(_PROJECT_ROOT, "generalization_pipeline", "submission_candidate_apex35.py")
dst_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0120", "candidate")
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, "candidate_submission.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update strawberries target: "strawberries": 34, -> "strawberries": 24,
assert '"strawberries": 34,' in content
content = content.replace('"strawberries": 34,', '"strawberries": 24,  # EXP-0120')

# 2. Update opening_melons: "opening_melons": 9, -> "opening_melons": 14,
assert '"opening_melons": 9,' in content
content = content.replace('"opening_melons": 9,', '"opening_melons": 14,  # EXP-0120')

# 3. Update base_profile tomatoes: "tomatoes": 0, -> "tomatoes": 6,
assert '"tomatoes": 0,' in content
content = content.replace('"tomatoes": 0,', '"tomatoes": 6,  # EXP-0120')

with open(dst, "w", encoding="utf-8") as f:
    f.write(content)

h = hashlib.sha256(content.encode("utf-8")).hexdigest()
print(f"Generated {dst}")
print(f"Candidate Hash: {h}")
