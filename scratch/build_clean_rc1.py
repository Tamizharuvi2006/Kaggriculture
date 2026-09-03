import sys

with open(r"D:\kaggriculture\economic_brain_v2\submission_adaptive_v4_1_ev_dispatcher.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Original lines: {len(lines)}")

# We know the dead legacy section:
# Find where the dead legacy section starts (def _copy_action) and where it ends (before def _distance)
start_dead = None
end_dead = None

for i, line in enumerate(lines):
    if line.startswith("def _copy_action("):
        start_dead = i
    if line.startswith("def _distance("):
        end_dead = i

print(f"Dead section: lines {start_dead} to {end_dead} ({end_dead - start_dead} lines)")

# Cut out the dead section
clean_lines = lines[:start_dead] + lines[end_dead:]

print(f"Clean lines: {len(clean_lines)}")

with open(r"D:\kaggriculture\submission_v4_1_clean.py", "w", encoding="utf-8") as f:
    f.writelines(clean_lines)

print("Saved D:\\kaggriculture\\submission_v4_1_clean.py!")
