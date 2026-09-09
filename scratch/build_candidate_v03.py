import os

def build_cand_v03():
    # Start from V02 code
    v02_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v02.py"
    with open(v02_path, "r", encoding="utf-8") as f:
        code = f.read()

    # In agent(obs), after overlaid = _apply_market_interference...
    # Right before return _apply_fixed_board_adaptation(obs, overlaid)
    # Add Endgame Warehouse Clearance Flush on final steps (>= 715)
    target_return = "            return _apply_fixed_board_adaptation(obs, overlaid)"
    
    flush_logic = """            # Endgame Warehouse Clearance Flush (Steps >= 715)
            step_num = int(_get(obs, "step", 0))
            if step_num >= 715:
                private = _get(obs, "private", {}) or {}
                shed = _get(private, "shed", {}) or {}
                m_orders = overlaid.get("market", [])
                existing_sells = {o[1] for o in m_orders if o and o[0] == "SELL" and len(o) > 1}
                for prod in ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "FERTILIZER", "CARROT", "TOMATO", "EGG"):
                    qty = int(shed.get(prod, 0) or 0)
                    if qty > 0 and prod not in existing_sells and len(m_orders) < MAX_ORDERS:
                        m_orders.append(["SELL", prod, qty])
                overlaid["market"] = m_orders[:MAX_ORDERS]

            return _apply_fixed_board_adaptation(obs, overlaid)"""

    assert target_return in code, "Target return statement not found"
    code = code.replace(target_return, flush_logic, 1)

    os.makedirs(r"D:\kaggriculture\candidates", exist_ok=True)
    out_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v03.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully generated {out_path} ({len(code)} bytes)")

if __name__ == "__main__":
    build_cand_v03()
