with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    code = f.read()

# Put helper after future import
target_future = "from __future__ import annotations"
helper = """from __future__ import annotations

_LATEST_OBS = {}

def _get_opp_livestock():
    global _LATEST_OBS
    if not _LATEST_OBS: return 0
    farms = _LATEST_OBS.get("farms", [{}, {}]) if isinstance(_LATEST_OBS, dict) else getattr(_LATEST_OBS, "farms", [{}, {}])
    p = _LATEST_OBS.get("player", 0) if isinstance(_LATEST_OBS, dict) else getattr(_LATEST_OBS, "player", 0)
    opp_farm = farms[1 - p] if len(farms) > 1 else {}
    opp_tiles = opp_farm.get("tiles", []) if isinstance(opp_farm, dict) else getattr(opp_farm, "tiles", [])
    return sum(1 for r in opp_tiles for t in r if isinstance(t, dict) and t.get("animal"))
"""
assert target_future in code, "Target future not found"
code = code.replace(target_future, helper)

# Track obs in agent
target_agent_start = """    try:
        global _LATEST_PRICES"""
repl_agent_start = """    try:
        global _LATEST_PRICES, _LATEST_OBS
        _LATEST_OBS = obs"""
assert target_agent_start in code, "Target agent start not found"
code = code.replace(target_agent_start, repl_agent_start)

# Dynamic Opponent-Adaptive Herd Sizing
target_plan = """def _animal_plan():
    return _build_animal_plan(8, 4)"""

repl_plan = """def _animal_plan():
    opp_animals = _get_opp_livestock()
    # Opponent-Adaptive Sizing: If opponent is heavy livestock (>=3), cap herd at 3 cows to avoid milk glut
    if opp_animals >= 3:
        return _build_animal_plan(3, 0)
    elif opp_animals >= 2:
        return _build_animal_plan(5, 1)
    else:
        # Uncontested monopoly: capture full 8 cows + 2 sheep
        return _build_animal_plan(8, 2)"""
assert target_plan in code, "Target plan not found"
code = code.replace(target_plan, repl_plan)

with open(r"D:\kaggriculture\submission_rc13.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Created submission_rc13.py cleanly!")
