import os

def build_cand_v05():
    # Start from V04 code
    v04_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v04.py"
    with open(v04_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Locate the market intervention block in V04
    start_marker = "            step_num = int(_get(obs, \"step\", 0))"
    end_marker = "            return _apply_fixed_board_adaptation(obs, overlaid)"
    
    start_idx = code.find(start_marker)
    end_idx = code.find(end_marker)
    assert start_idx != -1 and end_idx != -1, "Markers not found"

    new_market_logic = """            step_num = int(_get(obs, "step", 0))
            day_num = step_num // 24
            private = _get(obs, "private", {}) or {}
            shed = _get(private, "shed", {}) or {}
            market_obs = _get(obs, "market", {}) or {}
            prices = _get(market_obs, "prices", {}) or {}
            m_orders = overlaid.get("market", [])

            # Dynamic Tiered Absorption Monetization (Steps 384 to 714)
            if 384 <= step_num < 715 and len(m_orders) < MAX_ORDERS:
                existing_sells = {o[1] for o in m_orders if o and o[0] == "SELL" and len(o) > 1}
                
                # Dynamic price floors depending on day progression
                # Early late-game (Days 16-22): target premium prices
                # Late-game (Days 23-28): accept base-market absorption to prevent Day-29 glut
                min_wool = 205 if day_num < 23 else 170
                min_milk = 185 if day_num < 23 else 145
                min_berry = 175 if day_num < 23 else 125
                min_melon = 200 if day_num < 23 else 150

                # Wool absorption sale
                w_qty = int(shed.get("WOOL", 0) or 0)
                if w_qty >= 2 and "WOOL" not in existing_sells and float(prices.get("WOOL", 0)) >= min_wool and len(m_orders) < MAX_ORDERS:
                    batch = min(3 if day_num >= 23 else 2, w_qty)
                    m_orders.append(["SELL", "WOOL", batch])
                    existing_sells.add("WOOL")

                # Milk absorption sale
                m_qty = int(shed.get("MILK", 0) or 0)
                if m_qty >= 3 and "MILK" not in existing_sells and float(prices.get("MILK", 0)) >= min_milk and len(m_orders) < MAX_ORDERS:
                    batch = min(4 if day_num >= 23 else 3, m_qty)
                    m_orders.append(["SELL", "MILK", batch])
                    existing_sells.add("MILK")

                # Strawberry absorption sale
                s_qty = int(shed.get("STRAWBERRY", 0) or 0)
                if s_qty >= 4 and "STRAWBERRY" not in existing_sells and float(prices.get("STRAWBERRY", 0)) >= min_berry and len(m_orders) < MAX_ORDERS:
                    batch = min(6 if day_num >= 23 else 4, s_qty)
                    m_orders.append(["SELL", "STRAWBERRY", batch])
                    existing_sells.add("STRAWBERRY")

                # Melon absorption sale
                ml_qty = int(shed.get("MELON", 0) or 0)
                if ml_qty >= 2 and "MELON" not in existing_sells and float(prices.get("MELON", 0)) >= min_melon and len(m_orders) < MAX_ORDERS:
                    batch = min(3, ml_qty)
                    m_orders.append(["SELL", "MELON", batch])
                    existing_sells.add("MELON")

                overlaid["market"] = m_orders[:MAX_ORDERS]

            # Endgame Warehouse Clearance Flush (Steps >= 715)
            elif step_num >= 715:
                existing_sells = {o[1] for o in m_orders if o and o[0] == "SELL" and len(o) > 1}
                for prod in ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "FERTILIZER", "CARROT", "TOMATO", "EGG"):
                    qty = int(shed.get(prod, 0) or 0)
                    if qty > 0 and prod not in existing_sells and len(m_orders) < MAX_ORDERS:
                        m_orders.append(["SELL", prod, qty])
                overlaid["market"] = m_orders[:MAX_ORDERS]

"""
    code = code[:start_idx] + new_market_logic + code[end_idx:]

    os.makedirs(r"D:\kaggriculture\candidates", exist_ok=True)
    out_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v05.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully generated {out_path} ({len(code)} bytes)")

if __name__ == "__main__":
    build_cand_v05()
