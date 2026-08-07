"""Research 30: Temporal ROI & Cutoff Day Analytics.

Computes the exact time-dependent Return-on-Investment (ROI per remaining turn until Day 30)
for every crop and livestock strategy across all 30 days of the game.

Formula:
  ROI(day) = Expected Net Profit ($) / Remaining Turns until Step 720

Determines the exact mathematical day cutoffs where ROI drops below zero or below opportunity cost.
"""

import sys
import os
import json
import time
import statistics

# Crop and Livestock Economic Profiles
# (Growth turns, seed cost, gross revenue per harvest)
CROP_PROFILES = {
    "STRAWBERRY": {"growth_days": 3, "growth_turns": 72, "seed_cost": 50.0, "avg_revenue": 211.61},
    "MELON": {"growth_days": 5, "growth_turns": 120, "seed_cost": 100.0, "avg_revenue": 240.00},
    "CARROT": {"growth_days": 2, "growth_turns": 48, "seed_cost": 15.0, "avg_revenue": 39.87},
    "WHEAT": {"growth_days": 2, "growth_turns": 48, "seed_cost": 10.0, "avg_revenue": 39.65},
    "COW": {"growth_days": 0, "growth_turns": 0, "animal_cost": 600.0, "daily_milk_revenue": 230.48, "daily_feed_cost": 39.65},
}


def compute_temporal_roi():
    total_days = 30
    turns_per_day = 24
    total_turns = total_days * turns_per_day

    daily_roi = {}

    for day in range(1, 31):
        remaining_days = total_days - day
        remaining_turns = remaining_days * turns_per_day

        daily_roi[day] = {}

        for crop, info in CROP_PROFILES.items():
            if crop == "COW":
                # Cow generates daily net revenue until Day 30
                net_daily = info["daily_milk_revenue"] - info["daily_feed_cost"]
                total_net = (net_daily * remaining_days) - info["animal_cost"]
                roi_per_turn = total_net / max(1, remaining_turns) if remaining_turns > 0 else -600.0
            else:
                growth_days = info["growth_days"]
                # Number of full harvest cycles possible in remaining days
                cycles = remaining_days // growth_days
                if cycles >= 1:
                    total_net = cycles * (info["avg_revenue"] - info["seed_cost"])
                    roi_per_turn = total_net / max(1, remaining_turns)
                else:
                    # Un-matured crop trap! (0 cycles completed)
                    total_net = -info["seed_cost"]
                    roi_per_turn = total_net / max(1, remaining_turns) if remaining_turns > 0 else -info["seed_cost"]

            daily_roi[day][crop] = round(roi_per_turn, 2)

    return daily_roi


def main():
    print("=" * 90)
    print(" RESEARCH 30: TEMPORAL ROI & CUTOFF DAY ANALYTICS")
    print("=" * 90)

    daily_roi = compute_temporal_roi()

    print(f"{'Day':<5} | {'Remaining Days':<15} | {'Strawberry ROI ($/t)':<20} | {'Melon ROI ($/t)':<18} | {'Cow ROI ($/t)':<15}")
    print("-" * 80)
    for day in range(1, 31):
        rem = 30 - day
        s_roi = daily_roi[day]["STRAWBERRY"]
        m_roi = daily_roi[day]["MELON"]
        c_roi = daily_roi[day]["COW"]
        print(f"{day:<5} | {rem:<15} | ${s_roi:<19.2f} | ${m_roi:<17.2f} | ${c_roi:<14.2f}")
    print("=" * 80)

    # Determine exact ROI cutoffs
    straw_cutoff = max(d for d in range(1, 31) if daily_roi[d]["STRAWBERRY"] > 0)
    melon_cutoff = max(d for d in range(1, 31) if daily_roi[d]["MELON"] > 0)
    cow_cutoff = max(d for d in range(1, 31) if daily_roi[d]["COW"] > 0)

    print("\nEXACT MATHEMATICAL TEMPORAL ROI CUTOFF DAYS:")
    print(f"  - Strawberry Planting Cutoff Day:  Day {straw_cutoff} (Day {straw_cutoff+1}+ has negative ROI / un-matured trap)")
    print(f"  - Melon Planting Cutoff Day:       Day {melon_cutoff} (Day {melon_cutoff+1}+ has negative ROI / un-matured trap)")
    print(f"  - Cow Purchase Cutoff Day:         Day {cow_cutoff} (Day {cow_cutoff+1}+ has negative ROI / capital lockup)\n")

    report = {
        "daily_roi": daily_roi,
        "cutoffs": {
            "STRAWBERRY": straw_cutoff,
            "MELON": melon_cutoff,
            "COW": cow_cutoff,
        },
    }

    with open("research30_temporal_roi_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research30_temporal_roi_results.json")


if __name__ == "__main__":
    main()
