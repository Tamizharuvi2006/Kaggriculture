with open("submission_h6_adaptive_allocation.py", "r") as f:
    code = f.read()

target = "if opp_s > 8:"
replacement = "if opp_s >= 16:"

assert target in code, "target string not found in submission_h6_adaptive_allocation.py"

code = code.replace(target, replacement, 1)

with open("submission_h6_threshold16.py", "w") as f:
    f.write(code)

print("Generated submission_h6_threshold16.py successfully!")
