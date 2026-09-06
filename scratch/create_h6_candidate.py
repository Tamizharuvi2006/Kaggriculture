with open("submission_rc2_terminal_horizon.py", "r") as f:
    code = f.read()

# 1. Add global _OPP_STRAWBERRIES tracking in _observe_opponent
target_obs = """    opponent = farms[1 - player]
    tiles = [tile for row in (_get(opponent, "tiles", []) or []) for tile in row if isinstance(tile, dict)]
    plants = sum(tile.get("kind") == "PLANT" for tile in tiles)
    wheat = sum(tile.get("crop") == "WHEAT" for tile in tiles)
    strawberries = sum(tile.get("crop") == "STRAWBERRY" for tile in tiles)"""

replacement_obs = """    global _OPP_STRAWBERRIES
    opponent = farms[1 - player]
    tiles = [tile for row in (_get(opponent, "tiles", []) or []) for tile in row if isinstance(tile, dict)]
    plants = sum(tile.get("kind") == "PLANT" for tile in tiles)
    wheat = sum(tile.get("crop") == "WHEAT" for tile in tiles)
    strawberries = sum(tile.get("crop") == "STRAWBERRY" for tile in tiles)
    _OPP_STRAWBERRIES = strawberries"""

# 2. Modify _crop_plan to adapt primary_quota
target_plan = """    # B. Allocate primary cash crop (85% of remaining arable plots)
    rem = candidates[total_wheat_plots:]
    primary_quota = max(0, int(len(rem) * 0.85))
    for pos in rem[:primary_quota]:
        plan[pos] = primary_cash_crop"""

replacement_plan = """    # B. Allocate primary cash crop (85% of remaining arable plots)
    rem = candidates[total_wheat_plots:]
    primary_quota = max(0, int(len(rem) * 0.85))

    # H6: Adaptive Strawberry Allocation Sizing (Town Absorption - Opponent Exposure)
    if primary_cash_crop == "STRAWBERRY" and day >= 11:
        opp_s = globals().get("_OPP_STRAWBERRIES", 0)
        if opp_s > 8:
            safe_quota = max(10, 26 - opp_s)
            primary_quota = min(primary_quota, safe_quota)

    for pos in rem[:primary_quota]:
        plan[pos] = primary_cash_crop"""

# 3. Add _OPP_STRAWBERRIES = 0 at top module level
top_init = "_OPP_STRAWBERRIES = 0\n"

assert target_obs in code, "target_obs not found!"
assert target_plan in code, "target_plan not found!"

code = top_init + code.replace(target_obs, replacement_obs, 1).replace(target_plan, replacement_plan, 1)

with open("submission_h6_adaptive_allocation.py", "w") as f:
    f.write(code)

print("Successfully generated submission_h6_adaptive_allocation.py!")
