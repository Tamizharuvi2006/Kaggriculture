"""Experiment 001: Exact v1.32.7 Market Knee Sweep directly against installed kaggle_environments."""
from __future__ import annotations
import kaggle_environments
from kaggle_environments.envs.kaggriculture.kaggriculture import MARKET_PARAMS, market_price, MARKET_I0, SHOPS

def run_knee_sweep():
    print("=" * 80)
    print(f"KAGGRICULTURE v{kaggle_environments.__version__} EXACT GROUND TRUTH MARKET KNEE SWEEP")
    print("=" * 80)

    commodities = ["CARROT", "TOMATO", "EGG", "MELON", "STRAWBERRY", "MILK", "WHEAT"]
    u_samples = [0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0]

    for comm in commodities:
        p_cfg = MARKET_PARAMS[comm]
        base = p_cfg["base"]
        T = p_cfg["T"]
        below_func = p_cfg.get("below_func")
        above_func = p_cfg.get("above_func")
        below_target = p_cfg.get("below_target")
        
        print(f"\n>>> Commodity: {comm} | Base: ${base} | T: {T} | Below: {below_func} (target: {below_target}) | Above: {above_func}")
        print(f"{'u':>6} | {'Inventory':>10} | {'Drained (I0-Inv)':>18} | {'Exact Price':>12} | {'Price/Base':>10}")
        print("-" * 65)
        
        for u in u_samples:
            drained = u * T
            inv = MARKET_I0 - drained
            price = market_price(comm, inv)
            ratio = price / base
            print(f"{u:6.2f} | {inv:10.1f} | {drained:18.1f} | ${price:11d} | {ratio:9.2f}x")

    print("\n" + "=" * 80)
    print("GLUT / OVER-SUPPLY SWEEP (Inventory > I0):")
    print("=" * 80)
    glut_units = [0, 25, 50, 100, 200, 300, 500, 1000]
    for comm in commodities:
        p_cfg = MARKET_PARAMS[comm]
        base = p_cfg["base"]
        T = p_cfg["T"]
        above_func = p_cfg.get("above_func")
        above_target = p_cfg.get("above_target")
        print(f"\n>>> Commodity: {comm} (Base: ${base}, T: {T}, Above: {above_func}, target: {above_target})")
        print(f"{'Glut Units':>12} | {'Inventory':>10} | {'Exact Price':>12} | {'Price/Base':>10}")
        print("-" * 55)
        for g in glut_units:
            inv = MARKET_I0 + g
            price = market_price(comm, inv)
            ratio = price / base
            print(f"{g:12d} | {inv:10.1f} | ${price:12d} | {ratio:9.2f}x")

    print("\n" + "=" * 80)
    print("TOWN SHOP DRAIN TRAJECTORY ANALYSIS (Realistic Game Trajectories):")
    print("=" * 80)
    print("Shop drain rates per 24-step day:")
    for shop_name, prods in sorted(SHOPS.items()):
        mult = 2 if len(prods) == 1 else 1
        drain_per_day = (24 // 4) * mult  # 6 * mult units/day
        print(f"  - {shop_name:<16}: {prods} -> {drain_per_day} units/day per shop instance")

if __name__ == "__main__":
    run_knee_sweep()
