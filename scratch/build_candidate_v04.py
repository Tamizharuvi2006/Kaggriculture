import os

def build_cand_v04():
    # Start from V03 code
    v03_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v03.py"
    with open(v03_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Find the flush logic in V03 and augment it with Mid-Game Smooth Absorption Selling
    old_flush = """            # Endgame Warehouse Clearance Flush (Steps >= 715)
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

    new_flush = """            step_num = int(_get(obs, "step", 0))
            private = _get(obs, "private", {}) or {}
            shed = _get(private, "shed", {}) or {}
            market_obs = _get(obs, "market", {}) or {}
            prices = _get(market_obs, "prices", {}) or {}
            m_orders = overlaid.get("market", [])

            # 1. Mid-Game Smooth Absorption Selling (Steps 384 to 714)
            # Sell surplus high-value stock in small tranches when prices are near peak
            if 384 <= step_num < 715 and len(m_orders) < MAX_ORDERS:
                existing_sells = {o[1] for o in m_orders if o and o[0] == "SELL" and len(o) > 1}
                # Wool absorption sale
                w_qty = int(shed.get("WOOL", 0) or 0)
                if w_qty >= 2 and "WOOL" not in existing_sells and float(prices.get("WOOL", 0)) >= 210 and len(m_orders) < MAX_ORDERS:
                    batch = min(2, w_qty)
                    m_orders.append(["SELL", "WOOL", batch])
                    existing_sells.add("WOOL")

                # Milk absorption sale
                m_qty = int(shed.get("MILK", 0) or 0)
                if m_qty >= 3 and "MILK" not in existing_sells and float(prices.get("MILK", 0)) >= 190 and len(m_orders) < MAX_ORDERS:
                    batch = min(3, m_qty)
                    m_orders.append(["SELL", "MILK", batch])
                    existing_sells.add("MILK")

                # Strawberry absorption sale
                s_qty = int(shed.get("STRAWBERRY", 0) or 0)
                if s_qty >= 4 and "STRAWBERRY" not in existing_sells and float(prices.get("STRAWBERRY", 0)) >= 180 and len(m_orders) < MAX_ORDERS:
                    batch = min(4, s_qty)
                    m_orders.append(["SELL", "STRAWBERRY", batch])
                    existing_sells.add("STRAWBERRY")

                overlaid["market"] = m_orders[:MAX_ORDERS]

            # 2. Endgame Warehouse Clearance Flush (Steps >= 715)
            elif step_num >= 715:
                existing_sells = {o[1] for o in m_orders if o and o[0] == "SELL" and len(o) > 1}
                for prod in ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "FERTILIZER", "CARROT", "TOMATO", "EGG"):
                    qty = int(shed.get(prod, 0) or 0)
                    if qty > 0 and prod not in existing_sells and len(m_orders) < MAX_ORDERS:
                        m_orders.append(["SELL", prod, qty])
                overlaid["market"] = m_orders[:MAX_ORDERS]

            return _apply_fixed_board_adaptation(obs, overlaid)"""

    assert old_flush in code, "Old flush block not found"
    code = code.replace(old_flush, new_flush, 1)

    os.makedirs(r"D:\kaggriculture\candidates", exist_ok=True)
    out_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v04.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully generated {out_path} ({len(code)} bytes)")

if __name__ == "__main__":
    build_cand_v04()
