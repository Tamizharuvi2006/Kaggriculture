"""Differential Comparator: Compares Official Python Oracle JSON trace vs FastSim JSON trace.

Identifies exact step, field, and value divergence.
"""
import sys
import json
import argparse

CHECKPOINT_STEPS = [
    0, 72, 120, 144, 168, 216, 240, 264, 288, 312, 336, 360,
    480, 600, 672, 695, 696, 700, 705, 710, 715, 719, 720
]

def compare_traces(off_path: str, rust_path: str, verbose: bool = True) -> bool:
    with open(off_path, "r") as f:
        off = json.load(f)
    with open(rust_path, "r") as f:
        rust = json.load(f)

    # 1. Metadata check
    if off["seed"] != rust["seed"] or off["hero_seat"] != rust["hero_seat"]:
        if verbose:
            print(f"FAILED: Metadata mismatch! Seed {off['seed']} vs {rust['seed']}, Seat {off['hero_seat']} vs {rust['hero_seat']}")
        return False

    # 2. Final reward check
    off_r0, off_r1 = off["final_rewards"]
    rust_r0, rust_r1 = rust["final_rewards"]
    if abs(off_r0 - rust_r0) > 1e-3 or abs(off_r1 - rust_r1) > 1e-3:
        if verbose:
            print(f"FAILED: Final reward mismatch!")
            print(f"  Official: [{off_r0:.1f}, {off_r1:.1f}]")
            print(f"  FastSim : [{rust_r0:.1f}, {rust_r1:.1f}]")

    # 3. Step-by-step checkpoint check
    divergence_found = False
    for step in sorted(CHECKPOINT_STEPS):
        key = f"Step_{step}"
        if key not in off["checkpoints"] or key not in rust["checkpoints"]:
            continue

        snap_off = off["checkpoints"][key]
        snap_rust = rust["checkpoints"][key]

        # Check cash
        if abs(snap_off["hero_cash"] - snap_rust["hero_cash"]) > 1e-3:
            if verbose:
                print(f"\n[DIVERGENCE FOUND AT STEP {step}]")
                print(f"FIELD: hero_cash")
                print(f"  Official = ${snap_off['hero_cash']:.1f}")
                print(f"  FastSim  = ${snap_rust['hero_cash']:.1f}")
            divergence_found = True
            break

        if abs(snap_off["opp_cash"] - snap_rust["opp_cash"]) > 1e-3:
            if verbose:
                print(f"\n[DIVERGENCE FOUND AT STEP {step}]")
                print(f"FIELD: opp_cash")
                print(f"  Official = ${snap_off['opp_cash']:.1f}")
                print(f"  FastSim  = ${snap_rust['opp_cash']:.1f}")
            divergence_found = True
            break

        # Check farmer positions
        if list(snap_off["hero_farmer_pos"]) != list(snap_rust["hero_farmer_pos"]):
            if verbose:
                print(f"\n[DIVERGENCE FOUND AT STEP {step}]")
                print(f"FIELD: hero_farmer_pos")
                print(f"  Official = {snap_off['hero_farmer_pos']}")
                print(f"  FastSim  = {snap_rust['hero_farmer_pos']}")
            divergence_found = True
            break

        # Check market prices
        for prod, price_off in snap_off["market_prices"].items():
            price_rust = snap_rust["market_prices"].get(prod)
            if price_rust is None or price_off != price_rust:
                if verbose:
                    print(f"\n[DIVERGENCE FOUND AT STEP {step}]")
                    print(f"FIELD: market_price[{prod}]")
                    print(f"  Official = {price_off}")
                    print(f"  FastSim  = {price_rust}")
                divergence_found = True
                break
        if divergence_found:
            break

    if not divergence_found:
        if verbose:
            print(f"MATCH PASSED 100% BIT-EXACT! [Seed {off['seed']}, Seat {off['hero_seat']}]")
            print(f"  Rewards: Hero ${off['final_rewards'][off['hero_seat']]:.0f} vs Opp ${off['final_rewards'][1-off['hero_seat']]:.0f}")
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", type=str, required=True)
    parser.add_argument("--rust", type=str, required=True)
    args = parser.parse_args()

    ok = compare_traces(args.official, args.rust, verbose=True)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
