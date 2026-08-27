"""Inspect exact action trace of Cluster 87 (96.3% Win Rate, $120k+ mean reward)."""
import os
import json
import gzip
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE_PATH = os.path.join(BASE_DIR, "datasets", "il", "episodes", "93332287.json.gz")

def main():
    if not os.path.exists(TAPE_PATH):
        print("Missing tape:", TAPE_PATH)
        return

    with gzip.open(TAPE_PATH, "rt", encoding="utf-8") as f:
        data = json.load(f)

    steps = data.get("steps", [])
    print(f"Total steps in Episode 93332287: {len(steps)}")

    # Seat 0 is the elite agent
    seat = 0

    first_events = {
        "first_wheat": None,
        "first_carrot": None,
        "first_strawberry": None,
        "first_cow": None,
        "first_worker": None,
        "land_purchases": [],
        "animal_purchases": [],
    }

    daily_sales = defaultdict(lambda: defaultdict(float))
    plot_counts_by_day = {}

    for step_idx, step_data in enumerate(steps):
        day = (step_idx // 24) + 1
        hour = step_idx % 24

        state = step_data[seat]
        obs = state.get("observation", {})
        farms = obs.get("farms", [])
        my_farm = farms[seat] if len(farms) > seat else {}
        action = state.get("action", {})

        plots = my_farm.get("plots", [])
        crops_on_land = defaultdict(int)
        for p in plots:
            c = p.get("crop_type") or p.get("crop")
            if c:
                crops_on_land[c] += 1

        if hour == 23:
            plot_counts_by_day[day] = dict(crops_on_land)

        if isinstance(action, dict):
            for m in action.get("market", []):
                if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
                    daily_sales[day][m[1]] += m[2]
                if isinstance(m, list) and len(m) >= 2 and m[0] == "BUY":
                    item = m[1]
                    if "COW" in str(item) and first_events["first_cow"] is None:
                        first_events["first_cow"] = (day, hour, step_idx)

    print("\n--- CLUSTER 87 STRATEGIC TIMELINE (Ep 93332287) ---")
    print(f"First Cow Purchase: {first_events['first_cow']}")
    print("\nDaily Crop Distribution (End of Day):")
    for d in range(1, 31):
        if d in plot_counts_by_day:
            print(f"  Day {d:2d}: {plot_counts_by_day[d]}")

    print("\nDaily Market Sales:")
    for d in range(1, 31):
        if d in daily_sales:
            print(f"  Day {d:2d}: {dict(daily_sales[d])}")

if __name__ == "__main__":
    main()
