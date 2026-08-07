"""Research 14: Seed Oracle Experiment.

Determines whether seed inventory restrictions / scheduling disconnect is the true bottleneck.

Evaluates 3 Variants across 10 official benchmark seeds (Seeds 1000-1009):
- Variant A: Baseline V8.1 ($121.97k baseline configuration)
- Variant B: Seed Oracle (Modifies _build_tasks so empty farmland generates PLANT tasks even when seeds.get(crop, 0) == 0)
- Variant C: Auto-Buy Seeds (Modifies _market_orders to auto-purchase seeds whenever empty_tiles > 0 and cash > operating_reserve)

Logs:
- Average Score ($)
- Median Score ($)
- Avg Idle Workers / Turn
- Avg Empty Farmland Tiles / Turn
- Total Seeds Purchased
- Total Harvest Count

Questions Answered:
- If idle time drops significantly and score rises -> seed scheduling is the bottleneck.
- If score stays flat -> crop-plan caps are the real bottleneck.
"""

import sys
import os
import json
import importlib.util
import statistics
import time
import copy

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_oracle", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

V81_STRATEGY = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def run_variant(variant_name, seeds=list(range(1000, 1010))):
    print(f"\n--- Running {variant_name} across {len(seeds)} seeds ---")

    scores = []
    daily_idle_counts = []
    daily_empty_tiles = []
    seeds_purchased_list = []
    harvest_counts_list = []

    for seed in seeds:
        # Reset baseline configuration
        v18_mod.configure_strategy(dict(V81_STRATEGY))

        # Store original functions to restore later if patched
        orig_build_tasks = v18_mod._build_tasks
        orig_market_orders = v18_mod._market_orders

        if variant_name == "Variant B: Seed Oracle":
            def patched_build_tasks(obs, positions, inventories):
                player = int(v18_mod._get(obs, "player", 0))
                farm = v18_mod._get(obs, "farms", [])[player]
                tiles = v18_mod._get(farm, "tiles", [])
                private = v18_mod._get(obs, "private", {}) or {}
                seeds = v18_mod._get(private, "seeds", {}) or {}
                day = int(v18_mod._get(obs, "day", 0))
                unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
                crop_plan = v18_mod._crop_plan(day)

                tasks = orig_build_tasks(obs, positions, inventories)

                # Append PLANT tasks for any active crop_plan tile that is empty, even if seeds == 0
                for pos, crop in crop_plan.items():
                    x, y = pos
                    if y >= len(tiles) or x >= len(tiles[y]) or not v18_mod._active_target(pos, day, unlocked):
                        continue
                    tile = tiles[y][x]
                    if tile is None and day <= v18_mod._last_plant(crop):
                        # Add virtual plant task with priority 7
                        existing_plant = any(t[1] == pos and t[2][0] == "PLANT" for t in tasks)
                        if not existing_plant:
                            tasks.append(v18_mod._task(7, pos, ["PLANT", crop], None, "plant"))

                return tasks

            v18_mod._build_tasks = patched_build_tasks

        elif variant_name == "Variant C: Auto-Buy Seeds":
            def patched_market_orders(obs):
                orders = orig_market_orders(obs)

                # Check if there is remaining budget above operating reserve and empty tiles
                player = int(v18_mod._get(obs, "player", 0))
                farm = v18_mod._get(obs, "farms", [])[player]
                private = v18_mod._get(obs, "private", {}) or {}
                tiles = v18_mod._get(farm, "tiles", [])
                money = float(v18_mod._get(farm, "money", 0))
                day = int(v18_mod._get(obs, "day", 0))
                unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

                empty_count = 0
                for pos in v18_mod._crop_plan(day):
                    x, y = pos
                    if v18_mod._active_target(pos, day, unlocked):
                        if y < len(tiles) and x < len(tiles[y]) and tiles[y][x] is None:
                            empty_count += 1

                operating_reserve = 50.0
                if empty_count > 0 and money > operating_reserve and len(orders) < v18_mod.MAX_ORDERS:
                    # Pick best crop available
                    target_crop = "STRAWBERRY" if day >= 4 else "MELON" if day <= 3 else "WHEAT"
                    seed_cost = v18_mod.CROPS[target_crop]["seed"]
                    affordable = int((money - operating_reserve) // seed_cost)
                    buy_qty = min(empty_count, affordable)
                    if buy_qty > 0:
                        orders.append(["BUY_SEED", target_crop, buy_qty])

                return orders

            v18_mod._market_orders = patched_market_orders

        # Tracking metrics for seed simulation
        match_idle_count = 0
        match_empty_tiles = 0
        match_seeds_bought = 0
        match_harvests = 0

        def tracking_agent(obs):
            nonlocal match_idle_count, match_empty_tiles, match_seeds_bought, match_harvests

            # Inspect actions and observation
            player = int(v18_mod._get(obs, "player", 0))
            farm = v18_mod._get(obs, "farms", [])[player]
            tiles = v18_mod._get(farm, "tiles", [])
            unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

            empty_tiles = sum(
                1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                if v18_mod._active_target((x, y), int(obs.get("day", 0)), unlocked) and tiles[y][x] is None
            )
            match_empty_tiles += empty_tiles

            action_dict = v18_mod.agent(obs)

            farmer_act = action_dict.get("farmer", ["PASS"])
            hands_acts = action_dict.get("hands", [])
            all_acts = [farmer_act] + hands_acts

            for act in all_acts:
                if not act or act == ["PASS"]:
                    match_idle_count += 1
                elif act and len(act) > 0 and act[0] == "HARVEST":
                    match_harvests += 1

            for m_ord in action_dict.get("market", []):
                if m_ord and m_ord[0] == "BUY_SEED":
                    match_seeds_bought += int(m_ord[2]) if len(m_ord) > 2 else 1

            return action_dict

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state = env.run([tracking_agent, _noop_agent])

        # Restore original functions
        v18_mod._build_tasks = orig_build_tasks
        v18_mod._market_orders = orig_market_orders

        final_reward = state[-1][0]["reward"]
        scores.append(final_reward)
        daily_idle_counts.append(match_idle_count / 720.0)
        daily_empty_tiles.append(match_empty_tiles / 720.0)
        seeds_purchased_list.append(match_seeds_bought)
        harvest_counts_list.append(match_harvests)

    avg_score = statistics.mean(scores)
    median_score = statistics.median(scores)
    avg_idle = statistics.mean(daily_idle_counts)
    avg_empty = statistics.mean(daily_empty_tiles)
    avg_seeds = statistics.mean(seeds_purchased_list)
    avg_harvests = statistics.mean(harvest_counts_list)

    result = {
        "variant": variant_name,
        "avg_score": round(avg_score, 2),
        "median_score": round(median_score, 2),
        "avg_idle_workers_per_turn": round(avg_idle, 2),
        "avg_empty_farmland_tiles": round(avg_empty, 2),
        "avg_seeds_purchased": round(avg_seeds, 1),
        "avg_harvest_count": round(avg_harvests, 1),
        "scores": scores,
    }

    print(f"  Avg Score: ${avg_score:,.2f} | Median: ${median_score:,.2f}")
    print(f"  Avg Idle Workers / Turn: {avg_idle:.2f} | Avg Empty Tiles: {avg_empty:.2f}")
    print(f"  Avg Seeds Bought: {avg_seeds:.1f} | Avg Harvests: {avg_harvests:.1f}")

    return result


def main():
    print("=" * 80)
    print(" RESEARCH 14: SEED ORACLE EXPERIMENT (10 Matches per Variant)")
    print("=" * 80)

    seeds = list(range(1000, 1010))

    res_a = run_variant("Variant A: Baseline V8.1", seeds)
    res_b = run_variant("Variant B: Seed Oracle", seeds)
    res_c = run_variant("Variant C: Auto-Buy Seeds", seeds)

    report = {
        "variant_a_baseline": res_a,
        "variant_b_seed_oracle": res_b,
        "variant_c_autobuy_seeds": res_c,
    }

    print("\n" + "=" * 80)
    print(" RESEARCH 14: COMPARATIVE ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"{'Variant':<28} | {'Avg Score ($)':<14} | {'Median ($)':<12} | {'Idle W/Turn':<12} | {'Empty Tiles':<12}")
    print("-" * 85)
    for res in (res_a, res_b, res_c):
        print(
            f"{res['variant']:<28} | ${res['avg_score']:<13,.2f} | ${res['median_score']:<11,.2f} | {res['avg_idle_workers_per_turn']:<12.2f} | {res['avg_empty_farmland_tiles']:<12.2f}"
        )
    print("=" * 80)

    # Determine conclusion based on empirical data
    if res_b["avg_score"] > res_a["avg_score"] + 1000 or res_c["avg_score"] > res_a["avg_score"] + 1000:
        conclusion = "Seed inventory restrictions are the primary revenue bottleneck. Bypassing seed limits significantly boosts farm revenue."
    elif res_b["avg_idle_workers_per_turn"] < res_a["avg_idle_workers_per_turn"] - 0.5 and abs(res_b["avg_score"] - res_a["avg_score"]) < 1000:
        conclusion = "Seed limits cause idle worker turns, but crop-plan caps and crop ROI windows are the true score bottleneck (removing seed limits drops idle time but does not increase revenue)."
    else:
        conclusion = "Crop-plan static caps and animal labor contention are the true bottlenecks."

    report["empirical_conclusion"] = conclusion
    print(f"\nEMPIRICAL CONCLUSION: {conclusion}\n")

    with open("research14_seed_oracle_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full results to experiments/research14_seed_oracle_results.json")


if __name__ == "__main__":
    main()
