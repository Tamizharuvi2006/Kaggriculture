"""
Build Candidate Submission for EXP-0121 (CAND-121-02 Dynamic Land Unlock)
Mutates agent() in submission_candidate_apex35.py to dynamically trigger BUY_LAND
when step >= 120 and money >= 1100.0 and len(unlocked) == 1.
"""
import os
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.path.join(_PROJECT_ROOT, "generalization_pipeline", "submission_candidate_apex35.py")
dst_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0121", "candidate")
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, "candidate_submission.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# Inject dynamic land purchase logic right before final order filtering
target = '        # Enforce 3-quadrant ceiling'
injection = '''        # EXP-0121 CAND-121-02: Dynamic Land 2 Expansion when Cash >= $1,100 (Min Step 120)
        if step >= 120 and len(unlocked) == 1 and money >= 1100.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                market_orders.append(["BUY_LAND"])

        # Enforce 3-quadrant ceiling'''

assert target in content, "Target comment for order ceiling not found"
new_content = content.replace(target, injection)

with open(dst, "w", encoding="utf-8") as f:
    f.write(new_content)

h = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
print(f"Generated {dst}")
print(f"Candidate Hash: {h}")
