import os

def build_cand_v01():
    v41_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    with open(v41_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Enable fixed_board_adaptation in DEFAULT_STRATEGY
    target_str = '"fixed_board_adaptation": False,'
    replacement_str = '"fixed_board_adaptation": True,'
    assert target_str in code, "Target setting not found in code"
    code = code.replace(target_str, replacement_str, 1)

    # Locate _adaptive_animal_focus definition
    start_marker = "def _adaptive_animal_focus(obs, own, opponent):"
    end_marker = "def _prioritize_capital_orders("
    start_idx = code.find(start_marker)
    end_idx = code.find(end_marker)
    assert start_idx != -1 and end_idx != -1, "Function markers not found"

    new_fn = """def _adaptive_animal_focus(obs, own, opponent):
    \"\"\"Adapt livestock purchases based on Town Shop demand and real market prices.\"\"\"
    day = int(_get(obs, "day", 0))
    if day < 3 or day > 14:
        return None
    town = _get(obs, "town", {}) or {}
    shops = _get(town, "unlocked_shops", []) or []
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}

    milk_demand = sum(1 for s in shops if s in ("SMOOTHIE_SHOP", "PIZZA_SHOP", "ICE_CREAM_SHOP"))
    wool_demand = sum(1 for s in shops if s == "YARN_STORE")

    milk_price = float(prices.get("MILK", 160))
    wool_price = float(prices.get("WOOL", 200))

    # Steer herd towards high-demand commodity
    if wool_demand == 0 and milk_demand > 0:
        return "COW"
    elif wool_demand > 0 and milk_demand == 0:
        return "SHEEP"
    elif wool_demand > milk_demand:
        return "SHEEP"
    elif milk_demand > wool_demand:
        return "COW"
    else:
        # If tied, steer to current higher price
        if wool_price >= 200 and milk_price < 170:
            return "SHEEP"
        elif milk_price >= 190 and wool_price < 180:
            return "COW"
        elif milk_price >= wool_price:
            return "COW"
        else:
            return "SHEEP"


"""
    code = code[:start_idx] + new_fn + code[end_idx:]

    os.makedirs(r"D:\kaggriculture\candidates", exist_ok=True)
    out_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v01.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully generated {out_path} ({len(code)} bytes)")

if __name__ == "__main__":
    build_cand_v01()
