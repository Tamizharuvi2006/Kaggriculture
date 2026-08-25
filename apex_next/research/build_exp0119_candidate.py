"""
Build Candidate Submission for EXP-0119 (CAND-119-02)
Mutates single line in _build_tasks:
tasks.append(_task(7, pos, ["PLANT", crop], None, "plant"))
->
tasks.append(_task(4, pos, ["PLANT", crop], None, "plant"))
"""
import os
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.path.join(_PROJECT_ROOT, "generalization_pipeline", "submission_candidate_apex35.py")
dst_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0119", "candidate")
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, "candidate_submission.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

target = 'tasks.append(_task(7, pos, ["PLANT", crop], None, "plant"))'
replacement = 'tasks.append(_task(4, pos, ["PLANT", crop], None, "plant"))  # EXP-0119 CAND-119-02'

assert target in content, "Target PLANT priority 7 string not found"
new_content = content.replace(target, replacement)

with open(dst, "w", encoding="utf-8") as f:
    f.write(new_content)

h = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
print(f"Generated {dst}")
print(f"Candidate Hash: {h}")
