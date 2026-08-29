"""EXP150 Formal Detector Validation: Verifying 100% TPR and 0% FPR on real match dataset."""
from __future__ import annotations
import os
import sys
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

with open(os.path.join(REPORTS_DIR, "exp150_mirror_detector_results.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

all_matches = data["all_matches"]
mirror_matches = [m for m in all_matches if m["is_mirror"]]
non_mirror_matches = [m for m in all_matches if not m["is_mirror"]]

# Test Optimal Rules:
# Rule 1: Step 120 (Day 5) -> Straw >= 2 and Carrots == 0 and Sheep == 0
def rule_day5(snap):
    s120 = snap["step_120"]
    return s120["opp_straw"] >= 2 and s120["opp_carrots"] == 0 and s120["opp_sheep"] == 0

# Rule 2: Step 192 (Day 8) -> Straw >= 4 and Cows >= 4 and Carrots == 0 and Sheep == 0
def rule_day8(snap):
    s192 = snap["step_192"]
    return s192["opp_straw"] >= 4 and s192["opp_cows"] >= 4 and s192["opp_carrots"] == 0 and s192["opp_sheep"] == 0

# Rule 3: Step 216 (Day 9) -> Straw >= 8 and Cows >= 4 and Carrots == 0
def rule_day9(snap):
    s216 = snap["step_216"]
    return s216["opp_straw"] >= 8 and s216["opp_cows"] >= 4 and s216["opp_carrots"] == 0

rules = [
    ("Rule Day 5 (Step 120): Straw >= 2 & Carrots == 0 & Sheep == 0", rule_day5),
    ("Rule Day 8 (Step 192): Straw >= 4 & Cows >= 4 & Carrots == 0 & Sheep == 0", rule_day8),
    ("Rule Day 9 (Step 216): Straw >= 8 & Cows >= 4 & Carrots == 0", rule_day9),
]

print("=" * 145)
print("EXP150 OPTIMAL DETECTOR VERIFICATION SCORECARD:")
print("=" * 145)
print(f"{'Detector Name':<60} | {'True Positives':<18} | {'False Positives':<18} | {'Accuracy':<10} | {'TPR':<8} | {'FPR'}")
print("-" * 145)

for name, r_fn in rules:
    tp = sum(1 for m in mirror_matches if r_fn(m["snapshots"]))
    fp = sum(1 for m in non_mirror_matches if r_fn(m["snapshots"]))
    fn_c = len(mirror_matches) - tp
    tn = len(non_mirror_matches) - fp
    acc = (tp + tn) / len(all_matches) * 100
    tpr = (tp / len(mirror_matches)) * 100
    fpr = (fp / len(non_mirror_matches)) * 100
    print(f"{name:<60} | {tp:2d}/{len(mirror_matches)} ({tpr:5.1f}%){'':<6} | {fp:2d}/{len(non_mirror_matches)} ({fpr:5.1f}%){'':<6} | {acc:5.1f}%    | {tpr:5.1f}%  | {fpr:5.1f}%")

print("=" * 145)
