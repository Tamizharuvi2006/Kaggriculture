"""
Build Candidate Submission for EXP-0125 (CAND-125-02 Opponent Ripe Crop Front-Running)
Mutates agent() in submission_candidate_apex35.py to inspect opponent tiles and front-run
when opp_ripe_strawberries >= 4, straw_in_shed >= 2, and p_straw >= 110.0.
"""
import os
import hashlib

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.path.join(_PROJECT_ROOT, "generalization_pipeline", "submission_candidate_apex35.py")
dst_dir = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0125", "candidate")
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, "candidate_submission.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

target = '        # Enforce 3-quadrant ceiling'
injection = '''        # EXP-0125 CAND-125-02: Opponent Ripe Strawberry Front-Running
        opp_farm = farms[1] if len(farms) > 1 else {}
        opp_tiles = opp_farm.get("tiles") or []
        opp_ripe_straw = 0
        if isinstance(opp_tiles, list):
            for r in opp_tiles:
                if isinstance(r, list):
                    for c in r:
                        if isinstance(c, dict) and c.get("crop") == "STRAWBERRY" and c.get("stage") == "RIPE":
                            opp_ripe_straw += 1

        if opp_ripe_straw >= 4 and straw_in_shed >= 2 and p_straw >= 110.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])

        # Enforce 3-quadrant ceiling'''

assert target in content, "Target comment for order ceiling not found"
new_content = content.replace(target, injection)

with open(dst, "w", encoding="utf-8") as f:
    f.write(new_content)

h = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
print(f"Generated {dst}")
print(f"Candidate Hash: {h}")
