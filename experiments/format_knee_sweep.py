"""Experiment 001 Results Formatter."""
from __future__ import annotations
import json
import kaggle_environments
from kaggle_environments.envs.kaggriculture.kaggriculture import MARKET_PARAMS, market_price, MARKET_I0, SHOPS

def get_sweep_data():
    commodities = ["CARROT", "TOMATO", "EGG", "MELON", "STRAWBERRY", "MILK", "WHEAT"]
    u_samples = [0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0]
    
    results = {}
    for comm in commodities:
        p_cfg = MARKET_PARAMS[comm]
        base = p_cfg["base"]
        T = p_cfg["T"]
        below_func = p_cfg.get("below_func")
        above_func = p_cfg.get("above_func")
        below_target = p_cfg.get("below_target")
        
        rows = []
        for u in u_samples:
            drained = u * T
            inv = MARKET_I0 - drained
            price = market_price(comm, inv)
            ratio = round(price / base, 2)
            rows.append({
                "u": u,
                "inventory": inv,
                "drained": drained,
                "price": price,
                "ratio": ratio,
            })
        results[comm] = {
            "base": base,
            "T": T,
            "below_func": below_func,
            "above_func": above_func,
            "below_target": below_target,
            "rows": rows
        }
    return results

if __name__ == "__main__":
    data = get_sweep_data()
    for comm in ["CARROT", "TOMATO", "EGG", "MELON"]:
        cdata = data[comm]
        print(f"\n=================== {comm} (Base: ${cdata['base']}, T: {cdata['T']}, Below: {cdata['below_func']}) ===================")
        print(f"{'u':>6} | {'Inventory':>10} | {'Drained':>10} | {'Exact Price':>12} | {'Ratio':>8}")
        print("-" * 55)
        for r in cdata["rows"]:
            print(f"{r['u']:6.2f} | {r['inventory']:10.1f} | {r['drained']:10.1f} | ${r['price']:11d} | {r['ratio']:7.2f}x")
