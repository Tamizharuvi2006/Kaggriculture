with open("submission_rc4_1_clean.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """    # C. Allocate remaining plots to secondary cash crop (diversification buffer)
    for pos in rem[primary_quota:]:
        plan[pos] = secondary_cash_crop"""

replacement = """    # C. Allocate remaining plots to diversification buffer (RC4.2 Hybrid: 1 Carrot + 1 Wheat after confirmation)
    flex_rem = rem[primary_quota:]
    if globals().get("_FLOOD_CONFIRMED", False) and len(flex_rem) >= 2:
        plan[flex_rem[0]] = secondary_cash_crop
        plan[flex_rem[1]] = "WHEAT"
        for pos in flex_rem[2:]:
            plan[pos] = secondary_cash_crop
    else:
        for pos in flex_rem:
            plan[pos] = secondary_cash_crop"""

if target not in code:
    raise ValueError("Target block not found in submission_rc4_1_clean.py!")

new_code = code.replace(target, replacement, 1)

with open("submission_rc4_2_hybrid.py", "w", encoding="utf-8") as f:
    f.write(new_code)

print("Successfully written submission_rc4_2_hybrid.py")
