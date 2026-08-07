"""Research 17: Liquidity Shock Test.

Determines whether starting/early-game cash flow timing is the primary bottleneck.

Evaluates 4 Cash Injection Variants across 10 official benchmark seeds (Seeds 1000-1009):
- Variant A: Baseline V8.1 (+$0 starting cash)
- Variant B: +$1,000 Starting Cash Injection
- Variant C: +$3,000 Starting Cash Injection
- Variant D: +$5,000 Starting Cash Injection

Logs:
- Average Score ($)
- Median Score ($)
- Score Std Dev & Min/Max
- Avg Idle Workers / Turn
- Avg Empty Farmland Tiles / Turn
- Seeds Purchased
- Harvest Count

Questions Answered:
- If extra starting cash barely changes the score -> cash flow timing is NOT the bottleneck.
- If score rises sharply -> cash flow timing IS the primary bottleneck.
"""

import sys
import os
import json
import importlib.util
import statistics
import time

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_liquidity", v18_path)
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

VARIANTS = [
    {"label": "Variant A: Baseline V8.1 (+$0)", "cash_boost": 0.0},
    {"label": "Variant B: +$1,000 Cash Injection", "cash_boost": 1000.0},
    {"label": "Variant C: +$3,000 Cash Injection", "cash_boost": 3000.0},
    {"label": "Variant D: +$5,000 Cash Injection", "cash_boost": 5000.0},
]


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def run_liquidity_shock(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 17: LIQUIDITY SHOCK TEST (10 Matches per Variant)")
    print("=" * 80)

    results = []

    for v_info in VARIANTS:
        label = v_info["label"]
        cash_boost = v_info["cash_boost"]

        print(f"\n--- Benchmarking {label} (Cash Boost: +${cash_boost:,.0f}) ---")

        scores = []
        idle_worker_turns = []
        empty_tiles_list = []
        seeds_bought_list = []
        harvests_list = []

        for seed in seeds:
            v18_mod.configure_strategy(dict(V81_STRATEGY))

            match_idle = 0
            match_empty = 0
            match_seeds = 0
            match_harvests = 0
            cash_injected = False

            def tracking_agent(obs):
                nonlocal match_idle, match_empty, match_seeds, match_harvests, cash_injected

                player = int(v18_mod._get(obs, "player", 0))
                farm = v18_mod._get(obs, "farms", [])[player]

                # Inject cash boost into farm money on step 0
                if not cash_injected and cash_boost > 0:
                    current_money = float(farm.get("money", 0))
                    farm["money"] = current_money + cash_boost
                    cash_injected = True

                tiles = v18_mod._get(farm, "tiles", [])
                unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

                empty_count = sum(
                    1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                    if v18_mod._active_target((x, y), int(obs.get("day", 0)), unlocked) and tiles[y][x] is None
                )
                match_empty += empty_count

                action_dict = v18_mod.agent(obs)

                farmer_act = action_dict.get("farmer", ["PASS"])
                hands_acts = action_dict.get("hands", [])
                all_acts = [farmer_act] + hands_acts

                for act in all_acts:
                    if not act or act == ["PASS"]:
                        match_idle += 1
                    elif act and len(act) > 0 and act[0] == "HARVEST":
                        match_harvests += 1

                for m_ord in action_dict.get("market", []):
                    if m_ord and m_ord[0] == "BUY_SEED":
                        match_seeds += int(m_ord[2]) if len(m_ord) > 2 else 1

                return action_dict

            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            state = env.run([tracking_agent, _noop_agent])

            final_score = state[-1][0]["reward"]
            scores.append(final_score)
            idle_worker_turns.append(match_idle / 720.0)
            empty_tiles_list.append(match_empty / 720.0)
            seeds_bought_list.append(match_seeds)
            harvests_list.append(match_harvests)

        avg_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0

        avg_idle = statistics.mean(idle_worker_turns)
        avg_empty = statistics.mean(empty_tiles_list)
        avg_seeds = statistics.mean(seeds_bought_list)
        avg_harvests = statistics.mean(harvests_list)

        res = {
            "variant": label,
            "cash_boost": cash_boost,
            "avg_score": round(avg_score, 2),
            "median_score": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "avg_idle_workers_per_turn": round(avg_idle, 2),
            "avg_empty_farmland_tiles": round(avg_empty, 2),
            "avg_seeds_purchased": round(avg_seeds, 1),
            "avg_harvest_count": round(avg_harvests, 1),
            "scores": scores,
        }

        results.append(res)
        print(f"  Avg Score: ${avg_score:,.2f} | Median: ${median_score:,.2f} | StdDev: ${std_score:,.2f}")
        print(f"  Idle Workers: {avg_idle:.2f} | Empty Tiles: {avg_empty:.2f} | Seeds Bought: {avg_seeds:.1f}")

    # Summary table
    print("\n" + "=" * 85)
    print(" RESEARCH 17: LIQUIDITY SHOCK TEST SUMMARY")
    print("=" * 85)
    print(f"{'Variant Label':<32} | {'Avg Score ($)':<13} | {'Median ($)':<11} | {'Idle W/Turn':<11} | {'Empty Tiles':<11}")
    print("-" * 90)
    for r in results:
        print(f"{r['variant']:<32} | ${r['avg_score']:<12,.2f} | ${r['median_score']:<10,.2f} | {r['avg_idle_workers_per_turn']:<11.2f} | {r['avg_empty_farmland_tiles']:<11.2f}")
    print("=" * 85)

    base_score = results[0]["avg_score"]
    max_boost_score = max(r["avg_score"] for r in results[1:])
    diff = max_boost_score - base_score

    if diff > 3000:
        conclusion = "Cash flow timing IS the primary bottleneck. Injecting early cash significantly increases farm performance."
    else:
        conclusion = "Liquidity is NOT the primary bottleneck. Injecting extra cash barely changes final farm revenue."

    print(f"\nEMPIRICAL CONCLUSION: {conclusion}\n")

    report = {
        "results": results,
        "empirical_conclusion": conclusion,
    }

    with open("research17_liquidity_shock_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research17_liquidity_shock_results.json")

    return report


if __name__ == "__main__":
    run_liquidity_shock()
